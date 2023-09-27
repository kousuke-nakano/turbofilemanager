# turbofilemanager

`turbofilemanager` is a python package managing file transfers  as well as job submissions/collections from/to remote machines. `turbofilemanager` also support job-queuing systems such as PBS and Slurm. `turbofilemanager` relies on `rsync` and `scp` commands so that it works on a Linux-based machine.

![license](https://img.shields.io/github/license/kousuke-nakano/turbofilemanager) ![release](https://img.shields.io/github/release/kousuke-nakano/turbofilemanager/all.svg) ![fork](https://img.shields.io/github/forks/kousuke-nakano/turbofilemanager?style=social) ![stars](https://img.shields.io/github/stars/kousuke-nakano/turbofilemanager?style=social)

`turbofilemanager` software package provides two command-line tools:

- ``turbo-filemanager`` (managing file transfers)
- ``turbo-jobmanager`` (managing job submissions and collections)

## How to use ``turbo-filemanager``

    turbo-filemanager put -s remoteserver # transfer files in the current dir. to a remote server (remoteserver)
    turbo-filemanager get -s remoteserver # transfer files in the current dir. from a remote server (remoteserver)

## ``turbo-filemanager`` setup

When you run ``turbo-filemanager`` for the first time, ``turbofilemanager_config`` directory is created at your home directory. You should edit ``turbofilemanager_config/machine_handler_env/machine_data.yaml``. Here, the most important argument is ``file_manager_root``, which is explained later.

    # example of a remote computational server
    remoteserver:
    machine_type: remote
    queuing : True
    computation: True
    ip: XXX.XX.XX.XX
    ssh_port: 22
    username: xxxx/xxxxx
    file_manager_root: /home/xxxx/xxxx/xxxx
    ssh_key: ~/.ssh/xxxx
    ssh_option: -Y -A
    jobsubmit: /opt/pbs/bin/qsub
    jobcheck: /opt/pbs/bin/qstat
    jobdel: /opt/pbs/bin/qdel
    jobnum_index: 0

    # example of file-server
    remotefile:
    machine_type: remote
    queuing : False
    computation: False
    ip: XXX.XX.XX.XX
    ssh_port: 22
    username: xxxxxx
    file_manager_root: /mnt/aaaaa/bbbbb/ccccc
    ssh_key: ~/.ssh/xxxx
    ssh_option: -Y -A

    # example of localhost
    localhost:
    machine_type: local
    queuing : False
    computation: True
    username: None
    file_manager_root: /Users/xxxxx/yyyyy/zzzzz
    jobsubmit: bash
    jobcheck: ps
    jobnum_index: 1

If you install ``turbofilemanager`` on a login node of a computation server (i.e., if you want to submit jobs via a job-queuing command directly from the node where ``turbofilemanager`` is installed), you can set up like

    # example of a login node
    localhost:
    machine_type: local
    queuing : True
    computation: True
    username: None
    file_manager_root: /Users/xxxxxx/xxxxx/xxxxx
    jobsubmit: /opt/pbs/bin/qsub
    jobcheck: /opt/pbs/bin/qstat
    jobdel: /opt/pbs/bin/qdel
    jobnum_index: 0

Both ``turbo-filemanager`` and ``turbo-jobmanager`` work *only* in ``file_manager_root`` directory of the localhost.

``turbo-filemanager`` implements ``put`` and ``get`` commands. The commands transfer files from/to the ``localhost`` to/from a specified ``remotehost``. Concerning the destination, ``file_manager_root`` of the ``localhost`` is replaced with that of the ``remotehost``. For instance, suppose you are in ``/Users/xxxxx/yyyyy/zzzzz/kk/ll`` on your ``localhost`` whose ``file_manager_root`` is ``/Users/xxxxx/yyyyy/zzzzz/``. When you transfer the files in the current directory on ``localhost`` to ``nanashi`` whose ``file_manager_root`` is ``/mnt/aaaaa/bbbbb/ccccc`` by the ``put`` command, all the files in ``/Users/xxxxx/yyyyy/zzzzz/kk/ll`` on ``localhost`` will be transfered to ``/mnt/aaaaa/bbbbb/ccccc/kk/ll`` on ``nanashi``.

A remotehost can be specified by ``-s`` option. You can see ``--help``.

``turbo-filemanager`` transfers all the files in the current directory. If you want to include/exclude specific files, you can use ``--include``/``--exclude`` options. You can see ``--help``.

## ``turbo-jobmanager`` setup
Fisrt, you should set up ``turbo-filemanager`` because ``turbo-jobmanager`` uses ``turbo-filemanager`` for its file transfers.

When you run ``turbo-jobmanager`` for the first time, ``turbo-filemanager_config`` directory is created at your home directory. You should edit ``turbofilemanager_config/job_manager_env/machine_name/package.yaml``, ``turbofilemanager_config/job_manager_env/machine_name/submit.sh``, and ``turbofilemanager_config/job_manager_env/machine_name/queue_data.txt``.

    #package.yaml
    turborvb:
    name: turborvb
    binary_path:
        stable: /home/application/TurboRVB/bin
    binary_list:
        - turborvb-mpi.x
        - A
        - B
        - ...

    #queue_data.txt
    QUEUE   CORES  OMP  NODES  CPNS  MPI_PER_NODE  MAX_JOB_RUN  MAX_JOB_SUBMIT  MAX_TIME
    TINY     64    1    1       64    64           10           16               000:30:00
    SINGLE  128    1    1      128   128           10           16               168:00:00
    LONG    128    1    1      128   128           10           16               168:00:00
    SMALL   480    1    4      128   120           10           16               168:00:00
    SMALL   512    1    4      128   128           10           16               168:00:00

    #submit_mpi.sh (PBS)
    #!/bin/bash
    #PBS -q _QUEUE_
    #PBS -N _JOBNAME_
    #PBS -l walltime=_MAX_TIME_
    #PBS -j oe
    #PBS -l select=_NODES_:ncpus=_CORES_PER_NODE_:mpiprocs=_MPI_PER_NODE_
    #PBS -V

    # Note:
    # The variables _XXXXXX_ are replaced by job_manager.py.
    # Implemented arguments are:
    # QUEUE, JOBNAME, MAX_TIME, NODES, CORES_PER_NODE, MPI_PER_NODE
    # OMP_NUM_THREADS, NUM_CORES, INPUT, OUTPUT, BINARY_ROOT, BINARY
    # PREOPTION, POSTOPTION

    cd ${PBS_O_WORKDIR}

    export OMP_NUM_THREADS=_OMP_NUM_THREADS_

    CORES=_NUM_CORES_
    INPUT=_INPUT_
    OUTPUT=_OUTPUT_
    BINARY=_BINARY_ROOT_/_BINARY_

    mpirun -np $CORES $BINARY $PREOPTION < $INPUT $POSTOPTION > $OUTPUT

## How to use ``turbo-jobmanager``

    # for submissions
    turbo-jobmanager toss -s remoteserver -p turborvb -core 144
    # the default binary is the first one on package.yaml
    # queue, omp, etc... is automatically chosen from queue_data.txt.
    # the default inputfile/outputfile name is input.in/out.o respectively.
    # you can see --help

    # you can explicitly specify them, e.g.,
    turbo-jobmanager toss -s remoteserver -p turborvb -core 144 -b prep-mpi.x -omp 2 -i prep.input -o out_prep -q SINGLE

    # for collections
    jobmanager fetch

    # check running jobs
    jobmanager stat -s remoteserver

    # delete running jobs
    jobmanager del -s remoteserver -id XXXXX

    # show running jobs in the current directory
    jobmanager show

    # show the detail of a job
    jobmanager show -id XX
    # here XX is obtained by the above show command.

## Beta version
This is a **beta** version!!!! Contact the developers whenever you find bugs. Any suggestion is also welcome!

## Python modules
`turbofilemanager` can be also used in python scripts. See examples in the ``examples`` directory [ToBe].

# How to contribute

Work on the development or on a new branch

    git merge <new branch> development # if you work on a new branch.
    git push origin development

Check the next-version version

    # Confirm the version number via `setuptools-scm`
    python -m setuptools_scm
    e.g., 1.1.4.dev28+gceef293.d20221123 -> <next-version> = v1.1.4 or v1.1.4-alpha(for pre-release)

Add and push with the new tag

    # Push with tag
    git tag <next-version>  # e.g., git tag v1.1.4  # Do not forget "v" before the version number!
    git push origin development --tags  # or to the new branch
    
Send a pull request to the main branch on GitHub. 