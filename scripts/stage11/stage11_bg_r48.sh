#!/bin/bash
# stage11_bg_r48.sh - background launcher for the slow R=48 case.
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh
DIR=/home/yuan/data_sda/RUNS/runs/stage11/s2_W6_R48
cd "$DIR"
rm -rf output
mkdir output
/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main case.xml > run.log 2>&1
echo "RC=$?" >> run.log
echo "DONE marker" >> run.log
