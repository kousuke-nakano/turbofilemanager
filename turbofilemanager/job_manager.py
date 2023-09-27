# -*- coding: utf-8 -*-
import os

import pickle
import shutil
import yaml
import pandas as pd
import re
import time
from datetime import datetime
from collections import OrderedDict
from logging import getLogger, StreamHandler, Formatter
from typing import Optional

# file-manager related path lists
from turbofilemanager.file_manager_env import (
    job_manager_env_dir,
    file_manager_config_dir,
    job_manager_env_template_dir,
)
from turbofilemanager.data_transfer_manager import Machine, Data_transfer

yaml.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    lambda loader, node: OrderedDict(loader.construct_pairs(node)),
)

logger = getLogger("file-manager").getChild(__name__)


class Job_submission:
    stat_time_sleep = 60  # sec.

    def __init__(
        self,
        local_machine_name: str,
        client_machine_name: str,
        server_machine_name: str,
        # package related
        package: str,
        binary: Optional[str] = None,
        version: Optional[str] = None,
        input_file: Optional[str] = None,
        output_file: str = "out.o",
        preoption: Optional[str] = None,
        postoption: Optional[str] = None,
        input_redirect: bool = True,
        # job resources related
        cores: int = 1,
        openmp: int = 1,
        queue: Optional[str] = None,
        budget: Optional[str] = None,
        nompi: bool = False,
        # job information related
        jobname: str = "file-manager",
        pkl_name: str = "job_manager.pkl",
        safe_mode: bool = False,
        # bwlimit=1000
    ):

        self.local_machine = Machine(local_machine_name)
        self.client_machine = Machine(client_machine_name)
        self.server_machine = Machine(server_machine_name)
        # self.bwlimit = bwlimit

        self.data_transfer = Data_transfer(
            local_machine_name=local_machine_name,
            client_machine_name=client_machine_name,
            server_machine_name=server_machine_name,
            # bwlimit=bwlimit
        )

        if not self.server_machine.computation:
            logger.error("The server machine is not for computations!!!")
            raise ValueError

        # package and cores
        self.package = package
        logger.info(f"package={self.package}")
        self.cores = cores
        logger.info(f"cores={self.cores}")
        self.openmp = openmp
        logger.info(f"openmp={self.openmp}")

        # check config dir exists.
        if not os.path.isdir(job_manager_env_dir):
            logger.info(f"{job_manager_env_dir} is not found.")
            os.makedirs(file_manager_config_dir, exist_ok=True)
            shutil.copytree(job_manager_env_template_dir, job_manager_env_dir)
            logger.info(f"{job_manager_env_dir} has been generated.")
            logger.info(
                f"plz. edit directories and files in {job_manager_env_dir}"
            )
            return

        # open data files
        try:
            with open(
                os.path.join(
                    job_manager_env_dir,
                    self.server_machine.name,
                    "package.yaml",
                ),
                "r",
            ) as yf:
                data = yaml.safe_load(yf)
                self.package_data = data[package]
        except FileNotFoundError:
            logger.error(
                f"{os.path.join(job_manager_env_dir, self.server_machine.name, 'package.yaml')} is not found!!"
            )
            raise FileNotFoundError

        # version
        if version is None:
            logger.warning("version is not specified.")
            self.version = list(self.package_data["binary_path"].keys())[0]
            self.binary_path = list(self.package_data["binary_path"].values())[
                0
            ]
            logger.warning(f"default version is {self.version}")
            logger.warning(f"default binary_path is {self.binary_path}")

        else:
            if version not in self.package_data["binary_path"].keys():
                logger.error(
                    f"version={version} does not exist in binary_path. Plz. check package.yaml"
                )
                raise KeyError
            self.version = version
            self.binary_path = self.package_data["binary_path"][version]

        # binary
        if binary is None:
            logger.warning("binary is not specified.")
            self.binary = self.package_data["binary_list"][0]
            logger.warning(f"default binary is {self.binary}")
        else:
            if binary not in self.package_data["binary_list"]:
                logger.error(f"binary={binary}")
                logger.error(f"binary_list={self.package_data['binary_list']}")
                raise KeyError
            self.binary = binary

        # queue etc...
        if self.server_machine.queuing:
            try:
                queue_data_txt = os.path.join(
                    job_manager_env_dir,
                    self.server_machine.name,
                    "queue_data.txt",
                )
            except FileNotFoundError:
                logger.error(
                    f"{os.path.join(job_manager_env_dir, self.server_machine.name, 'queue_data.txt')} is not found!!"
                )
                raise FileNotFoundError

            pd_info = pd.read_csv(queue_data_txt, delim_whitespace=True)
            pd_core_omp = pd_info[
                (pd_info["CORES"] == self.cores)
                & (pd_info["OMP"] == self.openmp)
            ]
            pd_core_omp = pd_core_omp.reset_index(drop=True)
            if len(pd_core_omp) == 0:
                logger.error(
                    "No corresponding line exists Plz. check queue_data.txt"
                )
                raise KeyError

            if queue is None:
                self.queue = pd_core_omp["QUEUE"][0]
                self.nodes = pd_core_omp["NODES"][0]
                self.cpns = pd_core_omp["CPNS"][0]
                self.mpi_per_node = pd_core_omp["MPI_PER_NODE"][0]
                self.max_job_run = pd_core_omp["MAX_JOB_RUN"][0]
                self.max_job_submit = pd_core_omp["MAX_JOB_SUBMIT"][0]
                self.max_time = pd_core_omp["MAX_TIME"][0]
            else:
                pd_core_omp_queue = pd_core_omp[
                    (pd_core_omp["QUEUE"] == queue)
                ]
                pd_core_omp_queue = pd_core_omp_queue.reset_index(drop=True)
                if len(pd_core_omp_queue) == 0:
                    logger.error(
                        "No corresponding line exists Plz. check queue_data.txt"
                    )
                    raise KeyError
                if len(pd_core_omp_queue) > 1:
                    logger.error(
                        "There are more than two corresponding lines existing. Plz. check queue_data.txt"
                    )
                    raise KeyError
                self.queue = queue
                self.cpns = pd_core_omp_queue["CPNS"][0]
                self.nodes = pd_core_omp_queue["NODES"][0]
                self.mpi_per_node = pd_core_omp_queue["MPI_PER_NODE"][0]
                self.max_job_run = pd_core_omp_queue["MAX_JOB_RUN"][0]
                self.max_job_submit = pd_core_omp_queue["MAX_JOB_SUBMIT"][0]
                self.max_time = pd_core_omp_queue["MAX_TIME"][0]

        else:  # server_machine.queuing == False
            self.queue = None
            self.nodes = None
            self.cpns = None
            self.nodes = None
            self.mpi_per_node = None
            self.max_job_run = None
            self.max_job_submit = None
            self.max_time = None

        # other input information
        self.budget = budget
        self.jobname = jobname
        self.preoption = preoption
        self.postoption = postoption
        self.input_file = input_file
        self.output_file = output_file
        self.nompi = nompi
        self.pkl_name = pkl_name
        self.safe_mode = safe_mode
        self.input_redirect = input_redirect

        # job information!!
        self.job_number = None  # job ID.
        self.job_running = False  # 0: end, 1 running.
        self.job_dir = None
        self.job_submit_date = None
        self.job_check_last_time = None
        self.job_fetch_date = None
        self.job_status = (
            "unknown"  # one can put any comment. e.g. success or failure
        )

    def generate_script(self, submission_script: str = "submit.sh"):
        def replaced_lines(lines, keyword, value):
            buffer = [
                line for line in lines if re.match(f".*{keyword}.*", line)
            ]
            if len(buffer) == 0:
                return lines
            else:
                # assert len(buffer) == 1 # to be refactored.
                # buffer = buffer[0]
                for buf in buffer:
                    buffer_index = lines.index(buf)
                    lines[buffer_index] = lines[buffer_index].replace(
                        keyword.replace("\\", ""), str(value)
                    )
                return lines

        # mpi script or nompi script
        if self.nompi:
            submit_script = os.path.join(
                job_manager_env_dir,
                self.server_machine.name,
                "submit_nompi.sh",
            )
        else:
            submit_script = os.path.join(
                job_manager_env_dir, self.server_machine.name, "submit_mpi.sh"
            )

        with open(submit_script, "r") as f:
            lines = f.readlines()

        # Replacing keywords in submit_script
        # [NODES]
        lines = replaced_lines(lines, "_NODES_", self.nodes)
        # [CORE_PER_NODE]
        lines = replaced_lines(lines, "_CORES_PER_NODE_", self.cpns)
        # [MPI_PER_NODE]
        lines = replaced_lines(lines, "_MPI_PER_NODE_", self.mpi_per_node)
        # [MAX_TIME]
        lines = replaced_lines(lines, "_MAX_TIME_", self.max_time)
        # [JOB_NAME]
        lines = replaced_lines(lines, "_JOBNAME_", self.jobname)
        # [QUEUE]
        lines = replaced_lines(lines, "_QUEUE_", self.queue)
        # [OMP]
        lines = replaced_lines(lines, "_OMP_NUM_THREADS_", self.openmp)
        # [CORES]
        lines = replaced_lines(lines, "_NUM_CORES_", self.cores)
        # [BUDGET]
        lines = replaced_lines(lines, "_BUDGET_", self.budget)
        # [input and output]
        if self.input_file is None:
            lines = replaced_lines(lines, " < \$INPUT", "")
        else:
            lines = replaced_lines(lines, "_INPUT_", self.input_file)
            if not self.input_redirect:
                lines = replaced_lines(lines, " < \$INPUT", " $INPUT")
        lines = replaced_lines(lines, "_OUTPUT_", self.output_file)
        # [preoption]
        if self.preoption is None:
            lines = replaced_lines(lines, "\$PREOPTION", "")
        else:
            lines = replaced_lines(
                lines, "_PREOPTION_", '"' + self.preoption + '"'
            )
        # [postoption]
        if self.postoption is None:
            lines = replaced_lines(lines, "\$POSTOPTION", "")
        else:
            lines = replaced_lines(
                lines, "_POSTOPTION_", '"' + self.postoption + '"'
            )
        # [BINARY_ROOT] and [BINARY]
        if self.binary_path is None:
            lines = replaced_lines(lines, "_BINARY_ROOT_/", "")
        else:
            lines = replaced_lines(lines, "_BINARY_ROOT_", self.binary_path)
        lines = replaced_lines(lines, "_BINARY_", self.binary)

        with open(submission_script, "w") as f:
            f.writelines(lines)

        with open(self.pkl_name, "wb") as f:
            pickle.dump(self, f)

    def job_submit(
        self,
        submission_script: str = "submit.sh",
        from_objects: Optional[list] = None,
        include_list: Optional[list] = None,
        exclude_list: Optional[list] = None,
        dryrun_flag: bool = False,
        delete_flag: bool = False,
    ):
        if from_objects is None:
            from_objects = []
        if include_list is None:
            include_list = []
        if exclude_list is None:
            exclude_list = []

        if not self.jobnum_check():
            logger.info("The current num. job exceeds max")
            self.job_submit_date = None
            self.job_number = None
            self.job_running = False
            return False, self.job_number
        else:
            try:
                logger.debug("The computational node is available")
                command = (
                    f"{self.server_machine.jobsubmit} {submission_script}"
                )

                local_home = self.local_machine.file_manager_root
                client_home = self.client_machine.file_manager_root
                server_home = self.server_machine.file_manager_root
                if self.safe_mode:
                    if not self.local_machine.is_dir(local_home):
                        logger.error(f"{local_home} is not found.")
                        raise FileNotFoundError
                    if not self.client_machine.is_dir(client_home):
                        logger.error(f"{client_home} is not found.")
                        raise FileNotFoundError
                    if not self.server_machine.is_dir(server_home):
                        logger.error(f"{server_home} is not found.")
                        raise FileNotFoundError
                local_current_dir = os.path.abspath(os.getcwd())

                if not dryrun_flag:
                    if (
                        self.client_machine.machine_type == "local"
                        and self.server_machine.machine_type == "local"
                    ):
                        server_dir = local_current_dir
                    else:
                        if local_home not in local_current_dir:
                            logger.error(
                                "server-client_manager.py works only in the local_home dir."
                            )
                            raise ValueError
                        else:
                            client_dir = local_current_dir.replace(
                                local_home, client_home
                            )
                            server_dir = local_current_dir.replace(
                                local_home, server_home
                            )
                            logger.debug(client_dir)
                            logger.debug(server_dir)

                            # data transfer
                            self.data_transfer.put_objects(
                                from_objects=from_objects,
                                include_list=include_list,
                                exclude_list=exclude_list,
                                dryrun_flag=dryrun_flag,
                                delete_flag=delete_flag,
                            )
                            logger.debug("data trasfer is ok")

                    if self.server_machine.queuing:
                        logger.debug("queueing system")
                        (stdout, stderr,) = self.server_machine.run_command(
                            command=command, execute_dir=server_dir
                        )
                        logger.debug("command done")
                        logger.debug(stdout.split())
                        logger.debug(stderr.split())
                        self.job_number = stdout.split()[
                            self.server_machine.jobnum_index
                        ]
                        self.job_running = True
                        self.job_dir = server_dir
                        self.job_submit_date = datetime.today()
                    else:
                        self.server_machine.run_command(
                            command=command, execute_dir=server_dir
                        )
                        self.job_number = None
                        self.job_running = False
                        self.job_dir = server_dir
                        self.job_submit_date = datetime.today()

                    logger.info("Job submission is successful.")

                    with open(self.pkl_name, "wb") as f:
                        pickle.dump(self, f)

                    return True, self.job_number

                else:
                    logger.info("This is a dry-run")
                    return True, self.job_number

            except ValueError:
                self.job_number = None
                self.job_running = False
                logger.error("Something wrong in job_submit!!")

    def jobcheck(self):

        self.job_check_last_time = datetime.today()

        if self.server_machine.queuing:
            # if self.job_running:
            trial_num = 10
            jjj = 0
            while True:
                job_list = self.server_machine.get_job_list_as_text()
                logger.debug(job_list)
                if not job_list == "":
                    break
                if jjj > trial_num:
                    break
                logger.warning(
                    f"{self.server_machine.jobcheck} command did not work."
                )
                logger.warning(
                    f"The command will be retried after {self.stat_time_sleep}s sleep."
                )
                time.sleep(self.stat_time_sleep)
                jjj += 1
            if job_list == "" and jjj > trial_num:
                logger.error("Something wrong in jobcheck!!")
                raise ValueError
            bool_list = [
                True if re.match(f".*{self.job_number}.*", line) else False
                for line in job_list
            ]
            if any(bool_list):
                logger.info(f"job {self.job_number} is running.")
                self.job_running = True
                flag = True
            else:
                logger.info(f"job {self.job_number} has done.")
                self.job_running = False
                flag = False
            # else:
            #    flag = False
        else:
            flag = False

        with open(self.pkl_name, "wb") as f:
            pickle.dump(self, f)

        return flag

    def jobnum_check(self):
        if self.server_machine.queuing:
            job_list = self.server_machine.get_job_list_as_text()
            logger.debug(job_list)
            logger.debug(
                [
                    line
                    for line in job_list
                    if re.match(
                        f".*{self.server_machine.username}.*\s{self.queue}\s.*",
                        line,
                    )
                ]
            )
            bool_list = [
                True
                if re.match(
                    f".*{self.server_machine.username}.*\s{self.queue}\s.*",
                    line,
                )
                else False
                for line in job_list
            ]
            num = bool_list.count(True)
            logger.info(
                f"{num} jobs are running on {self.server_machine.name}"
            )
            if num < self.max_job_submit:
                logger.info(f"{num} < max_job_submit:{self.max_job_submit}")
                flag = True
            else:
                logger.info(f"{num} >= max_job_submit:{self.max_job_submit}")
                flag = False
        else:
            flag = True

        with open(self.pkl_name, "wb") as f:
            pickle.dump(self, f)

        return flag

    def fetch_job(
        self,
        from_objects: Optional[list] = None,
        include_list: Optional[list] = None,
        exclude_list: Optional[list] = None,
        dryrun_flag: bool = False,
        delete_flag: bool = False,
    ):
        if from_objects is None:
            from_objects = []
        if include_list is None:
            include_list = []
        if exclude_list is None:
            exclude_list = []
        local_home = self.local_machine.file_manager_root
        client_home = self.client_machine.file_manager_root
        server_home = self.server_machine.file_manager_root
        if self.safe_mode:
            if not self.local_machine.is_dir(local_home):
                logger.error(f"{local_home} is not found.")
                raise FileNotFoundError
            if not self.client_machine.is_dir(client_home):
                logger.error(f"{client_home} is not found.")
                raise FileNotFoundError
            if not self.server_machine.is_dir(server_home):
                logger.error(f"{server_home} is not found.")
                raise FileNotFoundError
        local_current_dir = os.path.abspath(os.getcwd())

        if not dryrun_flag:
            if (
                self.client_machine.machine_type == "local"
                and self.server_machine.machine_type == "local"
            ):
                server_dir = local_current_dir

            else:

                if local_home not in local_current_dir:
                    logger.error(
                        "server-client_manager.py works only in the local_home dir."
                    )
                    raise ValueError

                else:
                    client_dir = local_current_dir.replace(
                        local_home, client_home
                    )
                    server_dir = local_current_dir.replace(
                        local_home, server_home
                    )
                    logger.info(client_dir)
                    logger.info(server_dir)

                    # data transfer
                    self.data_transfer.get_objects(
                        from_objects=from_objects,
                        include_list=include_list,
                        exclude_list=exclude_list,
                        dryrun_flag=dryrun_flag,
                        delete_flag=delete_flag,
                    )

            self.job_fetch_date = datetime.today()
            with open(self.pkl_name, "wb") as f:
                pickle.dump(self, f)

        else:
            logger.info("This is a dry-run")

    def delete_job(self):
        # job delete
        self.server_machine.delete_job(jobid=self.job_number)
        self.job_running = False
        self.job_status = "failed"

        with open(self.pkl_name, "wb") as f:
            pickle.dump(self, f)


if __name__ == "__main__":
    from logging import getLogger
    from file_manager_env import file_manager_test_dir

    log_level = "DEBUG"
    logger = getLogger("file-manager")
    logger.setLevel(log_level)
    stream_handler = StreamHandler()
    stream_handler.setLevel(log_level)
    handler_format = Formatter(
        "Module-%(name)s, LogLevel-%(levelname)s, Line-%(lineno)d %(message)s"
    )
    stream_handler.setFormatter(handler_format)
    logger.addHandler(stream_handler)

    job_manager_test_dir = os.path.join(file_manager_test_dir, "job_manager")
    os.chdir(job_manager_test_dir)

    # moved to test
