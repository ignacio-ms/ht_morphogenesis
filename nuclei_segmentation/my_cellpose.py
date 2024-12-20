from scipy import ndimage

from cellpose import models, core
from cellpose.io import logger_setup

from auxiliary.utils.colors import bcolors as c
from auxiliary.data.dataset_ht import find_specimen
from auxiliary.utils.timer import timed
from auxiliary.data import imaging

from filtering.cardiac_region import get_margins, crop_img, restore_img
from feature_extraction.feature_extractor import filter_by_margin
from nuclei_segmentation.processing import preprocessing, postprocessing

# Configurations
use_gpu = core.use_gpu()
# use_gpu = False
print(f"GPU activated: {use_gpu}")
logger_setup()


def load_img(img_path, pipeline=None, test_name=None, verbose=0, **kwargs):
    """
    Load image with preprocessing.
    :param img_path: Path to image.
    :param pipeline: Preprocessing pipeline.
        Possible steps:
        normalization, equalization, anisodiff, bilateral,
        isotropy, gaussian, median, gamma, rescale_intensity
    :param test_name:
    :param verbose:
    :param kwargs:
    :return:
    """
    preprocess = preprocessing.Preprocessing(pipeline=pipeline)
    return preprocess.run(
        img_path, test_name=test_name,
        verbose=verbose, **kwargs
    )


def load_model(model_type='nuclei'):
    """
    Load cellpose model.
    :param model_type: Type of model to load. (nuclei, cyto)
        -nuclei: nuclei model
        -(cyto, cyto2, cyto3): cytoplasm model
        -tissuenet_cp3: tissuenet dataset.
        -livecell_cp3: livecell dataset
        -yeast_PhC_cp3: YEAZ dataset
        -yeast_BF_cp3: YEAZ dataset
        -bact_phase_cp3: omnipose dataset
        -bact_fluor_cp3: omnipose dataset
        -deepbacs_cp3: deepbacs dataset
        -cyto2_cp3: cellpose dataset
    :return: Model.
    """
    print(f'{c.OKBLUE}Loading model{c.ENDC}: {model_type}')
    if model_type in ['nuclei', 'cyto', 'cyto2', 'cyto3']:
        return models.Cellpose(gpu=use_gpu, model_type=model_type)

    return models.CellposeModel(model_type, diam_mean=17)


def run(
    model, img,
    diameter=None, channels=None,
    anisotropy=1,
    do_3D=False,
    stitch_threshold=.6,
    cellprob_threshold=0,
    flow_threshold=.4,
    verbose=0
):
    """
    Run cellpose on image.
    :param model: Cellpose model.
    :param img: Image.
    :param diameter: Diameter of nuclei. (Default: 0)
    :param channels: Channels to use. (Default: [0, 0])
    :param anisotropy: Anisotropy of image for sampling difference between XY and Z. (Default: 1)
    :param verbose: Verbosity level.
    :return: Masks.
    """

    if diameter is None:
        diameter = 17

    if channels is None:
        channels = [0, 0]

    if verbose:
        print(f'{c.OKGREEN}Image shape{c.ENDC}: {img.shape}')
        print(f'\t{c.BOLD}Diameter{c.ENDC}: {diameter}')
        print(f'\t{c.BOLD}Channels{c.ENDC}: {channels}')
        print(f'\t{c.BOLD}Anisotropy{c.ENDC}: {anisotropy}')
        print(f'\t{c.BOLD}Do 3D{c.ENDC}: {do_3D}')
        print(f'\t{c.BOLD}Stitch threshold{c.ENDC}: {stitch_threshold}')
        print(f'\t{c.BOLD}Cellprob threshold{c.ENDC}: {cellprob_threshold}')
        print(f'\t{c.BOLD}Flow threshold{c.ENDC}: {flow_threshold}')

    if isinstance(model, models.Cellpose):
        print(img.dtype, img.shape)
        masks, _, _, _ = model.eval(
            img,
            diameter=diameter,
            channels=channels,
            normalize=False,
            anisotropy=1,
            do_3D=do_3D,
            cellprob_threshold=cellprob_threshold,
            stitch_threshold=stitch_threshold,
            flow_threshold=flow_threshold,
        )

    else:
        masks, _, _ = model.eval(
            img,
            diameter=diameter,
            channels=channels,
            normalize=False,
            anisotropy=anisotropy,
            do_3D=do_3D,
            cellprob_threshold=cellprob_threshold,
            stitch_threshold=stitch_threshold,
            flow_threshold=flow_threshold,
        )

    if verbose:
        print(f'{c.OKGREEN}Masks shape{c.ENDC}: {masks.shape}')

    return masks


@timed
def predict(
    img_path, img_path_out,
    model, dataset,
    diameter, channels,
    tissue, verbose,
    **kwargs
):
    if 'test_name' in kwargs:
        img_path_out = img_path_out.replace('.nii.gz', f'_{kwargs["test_name"]}.nii.gz')

    # Set anisotropy
    metadata, _ = imaging.load_metadata(img_path)

    if tissue is not None:
        img = imaging.read_image(img_path, axes='ZYX')

        # Crop img by tissue
        specimen = find_specimen(img_path)
        lines_path, _ = dataset.read_line(specimen)

        margins = get_margins(
            line_path=lines_path, img_path=img_path,
            tissue=tissue, verbose=verbose
        )

        # Set margins to ZYX
        margins = (
            (margins[0][2], margins[0][1], margins[0][0]),
            (margins[1][2], margins[1][1], margins[1][0])
        )
        img = crop_img(img, margins, verbose=verbose)

    img = load_img(
        img_path,
        image=img if tissue is not None else None,
        test_name=kwargs['test_name'] if 'test_name' in kwargs else None,
        pipeline=kwargs['pipeline'] if 'pipeline' in kwargs else None,
        verbose=verbose
    )
    model = load_model(model_type=model)

    # Run segmentation
    masks = run(
        model, img,
        diameter=diameter,
        channels=channels,
        do_3D=kwargs['do_3D'] if 'do_3D' in kwargs else True,
        stitch_threshold=kwargs['stitch_threshold'] if 'stitch_threshold' in kwargs else None,
        cellprob_threshold=kwargs['cellprob_threshold'] if 'cellprob_threshold' in kwargs else .4,
        flow_threshold=kwargs['flow_threshold'] if 'flow_threshold' in kwargs else .4,
        verbose=verbose
    )

    # masks = filter_by_volume(masks, percentile=96, verbose=verbose)
    # Anisotropic recosntruction
    masks_reconstructed = preprocessing.reconstruct(masks, metadata=metadata)

    pp = postprocessing.PostProcessing(['clean_boundaries_opening'])
    masks_post = pp.run(masks_reconstructed, verbose=verbose)

    if tissue is not None:
        masks_post = filter_by_margin(masks_post, verbose=verbose)

        # Restore original shape
        masks_post = restore_img(
            masks_post, margins,
            depth=metadata['z_size'], resolution=metadata['x_size'],
            axes='ZYX', verbose=verbose
        )

    if isinstance(tissue, list):
        tissue = '_'.join(tissue)

    img_path_out = img_path_out.replace(
        '.nii.gz', f'_{tissue if tissue is not None else "all"}.nii.gz'
    )
    imaging.save_nii(masks_post, img_path_out, verbose=verbose, axes='ZYX')
