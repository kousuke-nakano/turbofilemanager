#!/bin/bash
# Note:
# The variables inside _xxx_ are replaced by job_manager.py.
# Implemented arguments are:
# QUEUE, JOBNAME, MAX_TIME, NODES, CORES_PER_NODE, MPI_PER_NODE
# OMP_NUM_THREADS, NUM_CORES, INPUT, OUTPUT, BINARY_ROOT, BINARY

export OMP_NUM_THREADS=_OMP_NUM_THREADS_

CORES=_NUM_CORES_
INPUT=_INPUT_
OUTPUT=_OUTPUT_
PREOPTION=_PREOPTION_
POSTOPTION=_POSTOPTION_
BINARY=_BINARY_ROOT_/_BINARY_

$BINARY $PREOPTION < $INPUT $POSTOPTION > $OUTPUT