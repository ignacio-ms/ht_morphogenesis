# Standard libraries
import os
import sys
import getopt

# Custom packages
try:
    current_dir = os.path.dirname(__file__)
except NameError:
    current_dir = os.getcwd()
sys.path.append(os.path.abspath(os.path.join(current_dir, os.pardir)))

from auxiliary import values as v
from auxiliary.utils.bash import arg_check
from auxiliary.utils.colors import bcolors as c
from auxiliary.data.dataset_ht import HtDataset, find_group
from auxiliary.utils.timer import LoadingBar

from meshes.utils.registration.cell_map_computation import CellTissueMap


def print_usage():
    print(
        'usage: run_cell_map.py -p <path> -i <image> -s <specimen> -gr <group> -v <verbose>'
        f'\n\n{c.BOLD}Arguments{c.ENDC}:'
        f'\n{c.BOLD}<path>{c.ENDC}: Path to data directory.'
        f'\n{c.BOLD}<specimen>{c.ENDC}: Specimen to run prediction on.'
        f'\n{c.BOLD}<group>{c.ENDC}: Group of specimens to run prediction on.'
        f'\n{c.BOLD}<verbose>{c.ENDC}: Verbosity level.'
    )
    sys.exit(2)


if __name__ == '__main__':
    argv = sys.argv[1:]

    data_path = v.data_path
    spec = None
    group = None
    tissue = 'myocardium'
    level = 'Membrane'
    feature = None
    verbose = 1

    try:
        opts, args = getopt.getopt(argv, 'hp:s:g:t:l:f:v:', [
            'help', 'path=', 'spec=', 'group=', 'tissue=', 'level=', 'feature=', 'verbose='
        ])

        if len(opts) > 5:
            print_usage()

        for opt, arg in opts:
            if opt in ('-h', '--help'):
                print_usage()
            elif opt in ('-p', '--path'):
                data_path = arg_check(opt, arg, '-p', '--path', str, print_usage)
            elif opt in ('-s', '--spec'):
                spec = arg_check(opt, arg, '-s', '--spec', str, print_usage)
            elif opt in ('-g', '--group'):
                group = arg_check(opt, arg, '-g', '--group', str, print_usage)
            elif opt in ('-t', '--tissue'):
                tissue = arg_check(opt, arg, '-t', '--tissue', str, print_usage)
            elif opt in ('-l', '--level'):
                level = arg_check(opt, arg, '-l', '--level', str, print_usage)
            elif opt in ('-f', '--feature'):
                feature = arg_check(opt, arg, '-f', '--feature', str, print_usage)
            elif opt in ('-v', '--verbose'):
                verbose = arg_check(opt, arg, '-v', '--verbose', int, print_usage)
            else:
                print(f'{c.FAIL}Invalid argument:{c.ENDC} {opt}')
                print_usage()

        dataset = HtDataset(data_path=data_path)

        if spec is not None:
            specimens = [spec]

        elif group is not None:
            if group in dataset.specimens:
                specimens = dataset.specimens[group]
            else:
                print(f'{c.FAIL}Invalid group{c.ENDC}: {group}')
                sys.exit(2)

        else:
            print(f'{c.FAIL}No group or specimen provided{c.ENDC}')
            sys.exit(2)

        if feature is None:
            print(f'{c.FAIL}No feature provided{c.ENDC}')
            sys.exit(2)

        bar = LoadingBar(len(specimens))
        for s in specimens:
            gr = find_group(s)
            print(f'{c.OKGREEN}Specimen{c.ENDC}: {s} ({gr})')
            try:
                cell_map = CellTissueMap(s, tissue=tissue, verbose=verbose)

                print(f'{c.OKBLUE}Type{c.ENDC}: {level}')
                if cell_map.mapping is None:
                    print(f'{c.WARNING}Waring{c.ENDC}: Mapping not found - computing')
                    cell_map.map_cells(type=level)
                    cell_map.get_neighborhood(radius=50)
                else:
                    print(f'{c.OKGREEN}Mapping{c.ENDC}: Found - skipping')
                    # cell_map.init_vars(type=level)
                _ = cell_map.color_mesh(feature, type=level, cmap='inferno_r')

            except Exception as e:
                print(f'{c.FAIL}Error{c.ENDC}: {e}')

                import traceback
                traceback.print_exc()

            bar.update()

        bar.end()

    except getopt.GetoptError:
        print_usage()