#!/bin/bash

index=$((SGE_TASK_ID - 1))

# Take arguments
while getopts 'p:v:' flag; do
  case "${flag}" in
    p) data_path="${OPTARG}" ;;
    v) verbose="${OPTARG}" ;;
    *) error "Unexpected option ${flag}" ;;
  esac
done

# 51 specimens - "0806_E5" "0208_E2" "0504_E1" "0521_E2" "0521_E4" "0516_E2" "0209_E2"
specimens=(
    "0503_E1" "0209_E1" "0520_E2" "0208_E3"
    "0308_E3" "0503_E2" "0516_E3"
    "0521_E1" "0523_E1" "0806_E3" "0806_E4" "0806_E6"
    "0401_E3" "0123_E1" "0122_E1" "0518_E3" "0521_E3"
    "0308_E2" "0401_E1" "0401_E2" "0502_E1" "0517_E2" "0806_E1" "0806_E2"
    "0308_E4" "0403_E2" "0404_E2" "0516_E5" "0517_E4"
    "0402_E1" "0402_E2" "0516_E4" "0517_E1" "0518_E2"
    "0119_E1" "0404_E1" "0515_E2" "0516_E1" "0518_E1" "0520_E1" "0520_E5"
    "0515_E1" "0520_E4"
    "0515_E3"
)

specimen=${specimens[$index]}
singularity exec -e -B /data_lab_MT/Ignacio/ht_morphogenesis:/repo/ -B $data_path:/data/ /data_lab_MT/Ignacio/mapping_cluster.sif python3 /repo/meshes/run_surface_map_cluster.py -p /data/ -s $specimen -v $verbose
singularity cache clean -f

