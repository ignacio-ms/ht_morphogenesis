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

# 20 specimens
specimens=(
  "0401_E3"
  "0521_E1"
  "0503_E2"
  "0209_E1"
  "0503_E1"
  "0518_E3" "0806_E6" "0504_E1"
  "0517_E1"
  "0806_E1" "0806_E4" "0806_E3" "0523_E1"
  "0516_E2" "0521_E4" "0806_E5"
  "0516_E3" "0209_E2" "0520_E2" "0520_E5"
)


# Loop over the specimens based on the array job index
specimen=${specimens[$index]}
echo "Processing specimen $specimen"
singularity exec -e -B /data_lab_MT/Ignacio/ht_morphogenesis:/app/ -B $data_path:/data/ /data_lab_MT/Ignacio/cluster_global.sif python3 /app/feature_extraction/run_extractor.py -d /data/ -s $specimen -t 'Nuclei' -l 'myocardium' -v $verbose
singularity cache clean -f
singularity exec -e -B /data_lab_MT/Ignacio/ht_morphogenesis:/app/ -B $data_path:/data/ /data_lab_MT/Ignacio/cluster_global.sif python3 /app/meshes/run_mesh_reconstruction.py -d /data/ -s $specimen -l 'Nuclei' -t 'myocardium' -v $verbose
singularity cache clean -f
singularity exec -e -B /data_lab_MT/Ignacio/ht_morphogenesis:/app/ -B $data_path:/data/ /data_lab_MT/Ignacio/cluster_global.sif python3 /app/meshes/run_extractor_complex.py -d /data/ -s $specimen -l 'Nuclei' -t 'myocardium' -m 0 -v $verbose
singularity cache clean -f
singularity exec -e -B /data_lab_MT/Ignacio/ht_morphogenesis:/app/ -B $data_path:/data/ /data_lab_MT/Ignacio/cluster_global.sif python3 /app/filtering/run_filter_tissue.py -d /data/ -s $specimen -l 'Nuclei' -t 'myocardium' -v $verbose
singularity cache clean -f
singularity exec -e -B /data_lab_MT/Ignacio/ht_morphogenesis:/app/ -B $data_path:/data/ /data_lab_MT/Ignacio/cluster_global.sif python3 /app/cell_division/run_cell_division.py -d /data/ -s $specimen -t 'myocardium' -v $verbose
singularity cache clean -f