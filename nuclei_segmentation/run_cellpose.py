# Standard libraries
import os
import sys
import getopt

from skimage import exposure

from cellpose import models, core

# Custom packages
try:
    current_dir = os.path.dirname(__file__)
except NameError:
    current_dir = os.getcwd()
sys.path.append(os.path.abspath(os.path.join(current_dir, os.pardir)))

from auxiliary.utils.bash import arg_check
from auxiliary.utils.colors import bcolors as c
from auxiliary.data.dataset_ht import HtDataset
from auxiliary.utils.timer import LoadingBar
from auxiliary.data import imaging

# Configurations
use_gpu = core.use_gpu()
print(f"GPU activated: {use_gpu}")

from cellpose.io import logger_setup
logger_setup();


def load_img(img_path, img_type='.nii.gz', equalize_img=True, verbose=0):
    """
    Load and normalize image.
    :param img_path: Path to image.
    :param img_type: Extension of image[.nii.gz | .tif]. (Default: .nii.gz)
    :param equalize_img: Perform histogram equalization on image. (Default: True)
    :param verbose: Verbosity level.
    :return: Image.
    """
    img = imaging.read_nii(img_path, axes='ZXY') if img_type == '.nii.gz' else None  # To be implemented
    if equalize_img:
        img = exposure.equalize_hist(img)

    if verbose:
        print(f'{c.OKBLUE}Loading image{c.ENDC}: {img_path}')
        print(f'{c.BOLD}Image shape{c.ENDC}: {img.shape}')

    return img


def load_model(model_type='nuclei', model_path=None):
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
    :param model_path: Path to model. (Default: None)
    :return: Model.
    """
    # Not needed at the moment
    if model_path is None:
        model_path = '../models/cellpose_models/'

    return models.Cellpose(gpu=use_gpu, model_type=model_type)


def run(
        model, img,
        diameter=None, channels=None,
        normalize=True,
):
    """
    Run cellpose on image.
    :param model: Cellpose model.
    :param img: Image.
    :param diameter: Diameter of nuclei. (Default: 0)
    :param channels: Channels to use. (Default: [0, 0])
    :param verbose: Verbosity level.
    :return: Masks.
    """

    if diameter is None:
        diameter = 17

    if channels is None:
        channels = [0, 0]

    masks, _, _, _ = model.eval(
        img,
        diameter=diameter,
        channels=channels,
        normalize=normalize,
        do_3D=True
    )

    return masks


def print_usage():
    """
    Print usage of script.
    """
    print(
        'usage: run_cellpose.py -i <image> -s <specimen> -gr <group> -m <model> -n <normalize> -e <equalize> -d <diameter> -c <channels> -v <verbose>'
        f'\n\n{c.BOLD}Options{c.ENDC}:\n'
        f'{c.BOLD}<image>{c.ENDC}: Path to image.\n'
        f'{c.BOLD}<specimen>{c.ENDC}: Specimen to predict.\n'
        f'\tIf <image> is not provided, <specimen> is used.\n'
        f'\tSpecimen must be in the format: XXXX_EY\n'
        f'{c.BOLD}<group>{c.ENDC}: Group to predict all remaining images.\n'
        f'\tIf <group> is not provided, <image> is used.\n'
        f'\tIn not <group> nor <image> nor <specimen> is provided, all remaining images are predicted.\n'
        f'{c.BOLD}<model>{c.ENDC}: Model to use. (Default: nuclei)\n'
        f'{c.BOLD}<normalize>{c.ENDC}: Normalize image. (Default: True)\n'
        f'{c.BOLD}<equalize>{c.ENDC}: Histogram equalization over image. (Default: True)\n'
        f'{c.BOLD}<diameter>{c.ENDC}: Diameter of nuclei. (Default: 17)\n'
        f'{c.BOLD}<channels>{c.ENDC}: Channels to use. (Default: [0, 0])\n'
        f'\tChannels must be a list of integers.\n'
        f'\t0 = Grayscale - 1 = Red - 2 = Green - 3 = Blue\n'
        f'{c.BOLD}<verbose>{c.ENDC}: Verbosity level. (Default: 0)\n'
    )
    sys.exit(2)


if __name__ == '__main__':
    argv = sys.argv[1:]

    img, spec, group, model, normalize, equalize, diameter, channels, verbose = None, None, None, None, None, None, None, None, None

    try:
        opts, args = getopt.getopt(argv, "i:s:gr:m:n:e:d:c:v:", [
            "image=", "specimen=", "group=", "model=", "normalize=", "equalize=", "diameter=", "channels=", "verbose="
        ])

        if len(opts) == 0 or len(opts) > 8:
            print_usage()

        for opt, arg in opts:
            if opt in ("-i", "--image"):
                img = arg_check(opt, arg, "-i", "--image", str, print_usage)
            if opt in ("-s", "--specimen"):
                spec = arg_check(opt, arg, "-s", "--specimen", str, print_usage)
            if opt in ("-gr", "--group"):
                group = arg_check(opt, arg, "-gr", "--group", str, print_usage)
            if opt in ("-m", "--model"):
                model = arg_check(opt, arg, "-m", "--model", str, print_usage)
            if opt in ("-n", "--normalize"):
                normalize = arg_check(opt, arg, "-n", "--normalize", bool, print_usage)
            if opt in ("-e", "--equalize"):
                equalize = arg_check(opt, arg, "-e", "--equalize", bool, print_usage)
            if opt in ("-d", "--diameter"):
                diameter = arg_check(opt, arg, "-d", "--diameter", int, print_usage)
            if opt in ("-c", "--channels"):
                channels = arg_check(opt, arg, "-c", "--channels", list, print_usage)
            if opt in ("-v", "--verbose"):
                verbose = arg_check(opt, arg, "-v", "--verbose", int, print_usage)
            else:
                print(f"{c.FAIL}Invalid option{c.ENDC}: {opt}")
                print_usage()

        if model is None:
            print(f'{c.BOLD}Model not provided{c.ENDC}: Running with default model (nuclei)')
            model = 'nuclei'

        dataset = HtDataset()

        if group is not None:
            if verbose:
                print(f'{c.OKBLUE}Running prediction on group{c.ENDC}: {group}')

            dataset.check_specimens(verbose=verbose)
            dataset.read_img_paths(type='RawImages')

            if group not in dataset.specimens.keys():
                print(f'{c.FAIL}Invalid group{c.ENDC}: {group}')
                print(f'{c.BOLD}Available groups{c.ENDC}: {list(dataset.specimens.keys())}')
                sys.exit(2)

            specimens = dataset.specimens[group]
            img_paths = dataset.raw_nuclei_path
            img_paths = [
                img_path for img_path in img_paths if any(
                    specimen in img_path for specimen in specimens
                )
            ]
            img_paths_out = [
                img_path.replace('RawImages', 'Segmentation')
                for img_path in img_paths
            ]

            img_paths_out = dataset.missing_nuclei_out
            img_paths_out = [
                img_path_out for img_path_out in img_paths_out if any(
                    specimen in img_path_out for specimen in specimens
                )
            ]

        elif img is not None:
            if verbose:
                print(f'{c.OKBLUE}Running prediction on image{c.ENDC}: {img}')

            img_paths = [img]
            img_paths_out = [img.replace('RawImages', 'Segmentation')]
            img_paths_out = [img_paths_out[0].replace('_DAPI_decon_0.5', 'mask')]

        elif spec is not None:
            if verbose:
                print(f'{c.OKBLUE}Running prediction on specimen{c.ENDC}: {spec}')

            img_path, img_path_out, _, _ = dataset.read_specimen(spec, verbose=verbose)
            img_paths = [img_path]
            img_path_out = [img_path_out]

        else:
            if verbose:
                print(f'Running prediction for all remaining images')

            dataset.check_specimens(verbose=verbose)
            img_paths = dataset.missing_nuclei
            img_paths_out = dataset.missing_nuclei_out

        if len(img_paths) == 0:
            print(f'{c.WARNING}No images to process{c.ENDC}')
            sys.exit(2)

        bar = LoadingBar(len(img_paths), length=50)
        for img_path, img_path_out in zip(img_paths, img_paths_out):
            img = load_img(img_path, equalize_img=equalize, verbose=verbose)
            model = load_model(model_type=model)

            masks = run(
                model, img,
                diameter=diameter, channels=channels,
                normalize=normalize
            )

            bar.update()
            imaging.save_prediction(masks, img_path_out, verbose=verbose)

    except getopt.GetoptError:
        print_usage()