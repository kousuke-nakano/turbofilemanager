#!/bin/bash
#PBS -q _QUEUE_
#PBS -N _JOBNAME_
#PBS -l walltime=_MAX_TIME_
#PBS -j oe
#PBS -l select=_NODES_:ncpus=_CORES_PER_NODE_:mpiprocs=_MPI_PER_NODE_
#PBS -V

# Note:
# The variables _xxx_ are replaced by job_manager.py.
# Implemented arguments are:
# QUEUE, JOBNAME, MAX_TIME, NODES, CORES_PER_NODE, MPI_PER_NODE
# OMP_NUM_THREADS, NUM_CORES, INPUT, OUTPUT, BINARY_ROOT, BINARY
# PREOPTION, POSTOPTION

cd ${PBS_O_WORKDIR}

module purge
module load oneapi-intel 

export OMP_NUM_THREADS=_OMP_NUM_THREADS_

CORES=_NUM_CORES_
INPUT=_INPUT_
PREOPTION=_PREOPTION_
POSTOPTION=_POSTOPTION_
OUTPUT=_OUTPUT_
BINARY=_BINARY_ROOT_/_BINARY_

$BINARY $PREOPTION < $INPUT $POSTOPTION > $OUTPUT
