#!/bin/bash

for i in {1..9}
do
    rsync -avhP --progress --no-perms --ignore-times /run/user/1003/gvfs/smb-share:server=tierra.cnic.es,share=sc/LAB_MT/LAB/Ignacio/Gr${i}/Features/* imarcoss@10.149.80.48:/data_lab_MT/Ignacio/data/data//Gr${i}/Features/
done
