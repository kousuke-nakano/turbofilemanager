# -*- coding: utf-8 -*-

# import python modules
import os
import time
from typing import Optional

import yaml
import shutil
import pathlib
import subprocess
from subprocess import PIPE

# define logger
from logging import getLogger, StreamHandler, Formatter

# import file-manager modules
from file_manager_env import (
    machine_handler_env_dir,
    file_manager_config_dir,
    machine_handler_env_template_dir,
)

logger = getLogger("file-manager").getChild(__name__)


class Machine:

    ssh_retry_time = 3600
    ssh_retry_max_num = 10

    def __init__(self, machine: str):
        self.machine_info_yaml = os.path.join(
            machine_handler_env_dir, "machine_data.yaml"
        )
        # logger.debug(self.machine_info_yaml)

        # check config dir exists.
        if not os.path.isdir(machine_handler_env_dir):
            logger.info(
                f"{machine_handler_env_dir} is not found. Probably, this is the first run."
            )
            os.makedirs(file_manager_config_dir, exist_ok=True)
            shutil.copytree(
                machine_handler_env_template_dir, machine_handler_env_dir
            )
            logger.info(f"{machine_handler_env_dir} has been generated.")
            logger.info(f"plz. edit {self.machine_info_yaml}")
            raise FileNotFoundError

        # open data files
        try:
            with open(self.machine_info_yaml, "r") as yf:
                self.data = yaml.safe_load(yf)[machine]
                # logger.debug(self.data)
        except FileNotFoundError:
            logger.error(
                f"The yaml file={self.machine_info_yaml} is not found!!"
            )
            raise FileNotFoundError
        except KeyError:
            logger.error(f"machine={machine} is not defined in the database!!")
            logger.error(
                "Plz. edit the following file according to the template."
            )
            logger.error(self.machine_info_yaml)
            raise KeyError

        self.__name = machine

    def __str__(self):

        output = [f"Machine obj. {self.name}"]
        return "\n".join(output)

    def get_value(self, key: str):
        try:
            return self.data[key]
        except KeyError:
            logger.error(f"{key} key is not defined in the database!!")
            logger.error(
                "Plz. edit the following file according to the template."
            )
            logger.error(self.machine_info_yaml)
            raise KeyError

    @property
    def name(self):
        return self.__name

    @property
    def machine_type(self):
        key = "machine_type"
        value = self.get_value(key=key)
        if value not in {"local", "remote"}:
            logger.error(f"value = {value}")
            logger.error("value should be local or remote")
            raise ValueError
        return value

    @property
    def ip(self):
        key = "ip"
        return self.get_value(key=key)

    @property
    def ssh_port(self):
        key = "ssh_port"
        return self.get_value(key=key)

    @property
    def username(self):
        key = "username"
        return self.get_value(key=key)

    @property
    def file_manager_root(self):
        key = "file_manager_root"
        return self.get_value(key=key)

    @property
    def ssh_key(self):
        key = "ssh_key"
        ssh_key_path = self.get_value(key=key)
        try:
            logger.debug(os.path.abspath(os.path.expanduser(ssh_key_path)))
            return os.path.abspath(os.path.expanduser(ssh_key_path))
        except FileNotFoundError:
            logger.error(f"{ssh_key_path} is not found!!.")
            raise FileNotFoundError

    @property
    def queuing(self):
        key = "queuing"
        return self.get_value(key=key)

    @property
    def computation(self):
        key = "computation"
        return self.get_value(key=key)

    @property
    def ssh_option(self):
        key = "ssh_option"
        return self.get_value(key=key)

    @property
    def jobsubmit(self):
        key = "jobsubmit"
        return self.get_value(key=key)

    @property
    def jobcheck(self):
        key = "jobcheck"
        return self.get_value(key=key)

    @property
    def jobdel(self):
        key = "jobdel"
        return self.get_value(key=key)

    @property
    def jobnum_index(self):
        key = "jobnum_index"
        return self.get_value(key=key)

    def get_job_list(self):
        command = f"{self.jobcheck}"
        stdout, stderr = self.run_command(command)
        return stdout, stderr

    def get_job_list_as_text(self):
        stdout, stderr = self.get_job_list()
        return stdout.split("\n")

    def delete_job(self, jobid: str):
        command = f"{self.jobdel} {jobid}"
        stdout, stderr = self.run_command(command)
        return stdout.split("\n")

    @staticmethod
    def local_run_command(command, execute_dir: Optional[str] = None):
        if execute_dir is None:
            command = f"{command}"
        else:
            if not os.path.isdir(execute_dir):
                logger.error(f"{execute_dir} is not found!")
                raise FileNotFoundError
            command = f"'cd {execute_dir}; {command}'"
        logger.debug(f"command = {command}")
        proc = subprocess.run(
            command, shell=True, stdout=PIPE, stderr=PIPE, text=True
        )
        return proc.stdout, proc.stderr

    def run_command(self, command, execute_dir: Optional[str] = None):
        trial_num = 10
        jjj = 0
        while True:
            if execute_dir is None:
                if self.machine_type == "remote":
                    command_r = f"ssh {self.username}@{self.ip} '{command}'"
                else:
                    command_r = f"{command}"
            else:
                if self.machine_type == "remote":
                    assert pathlib.Path(execute_dir).is_absolute()
                    command_r = f"ssh {self.username}@{self.ip} 'cd {execute_dir}; {command}'"
                else:
                    if not os.path.isdir(execute_dir):
                        logger.error(f"{execute_dir} is not found.")
                        raise FileNotFoundError
                    command_r = f"cd {execute_dir}; {command}"
            logger.debug(f"command = {command_r} in run_command")
            proc = subprocess.run(
                command_r, shell=True, stdout=PIPE, stderr=PIPE, text=True
            )
            if not proc.stderr:
                # success run_command
                logger.debug(f"stdout = {proc.stdout}")
                break
            else:
                # failure run_command
                logger.debug(f"stdout = {proc.stdout}")
                logger.debug(f"stderr = {proc.stderr}")
                logger.warning(f"command={command_r} did not work.")
                logger.warning(
                    f"The command will be retried after {self.ssh_retry_time}s sleep."
                )
                time.sleep(self.ssh_retry_time)
            if jjj > trial_num:
                break
            jjj += 1

        if jjj > trial_num:
            logger.error("Something wrong in run_command!!")
            raise ValueError

        return proc.stdout, proc.stderr

    def is_file(self, file_name: Optional[str]):
        logger.debug(f"check if file={file_name} exists.")
        assert pathlib.Path(file_name).is_absolute()
        cmd = f"test -f {file_name};echo $?"
        stdout, stderr = self.run_command(command=cmd)
        try:
            if int(stdout) == 0:
                logger.debug(f"Yes, file={file_name} exists on {self.name}.")
                return True
            else:
                logger.debug(
                    f"No, file={file_name} does not exist on {self.name}."
                )
                return False
        except ValueError:
            logger.error(
                "Something wrong in is_file(). Prpbably ssh did not work temporarily."
            )
            logger.error("Checking if the machine is reachable...")
            time.sleep(self.ssh_retry_time)
            if self.is_alive():
                return self.is_file(file_name=file_name)
            raise ValueError

    def is_dir(self, dir_name: Optional[str]):
        logger.debug(f"check if dir={dir_name} exists.")
        assert pathlib.Path(dir_name).is_absolute()
        cmd = f"test -d {dir_name};echo $?"
        stdout, stderr = self.run_command(command=cmd)
        try:
            if int(stdout) == 0:
                logger.debug(f"Yes, dir={dir_name} exists on {self.name}.")
                return True
            else:
                logger.debug(
                    f"No, dir={dir_name} does not exist on {self.name}."
                )
                return False
        except ValueError:
            logger.error(
                "Something wrong in is_dir(). Prpbably ssh did not work temporarily."
            )
            logger.error("Checking if the machine is reachable...")
            time.sleep(self.ssh_retry_time)
            if self.is_alive():
                return self.is_dir(dir_name=dir_name)
            raise ValueError

    def exist(self, object_name: Optional[str]):
        logger.debug(
            f"check if file or dir={object_name} exists on {self.name}."
        )
        cmd = f"test -e {object_name};echo $?"
        stdout, stderr = self.run_command(command=cmd)
        try:
            if int(stdout) == 0:
                logger.debug(
                    f"Yes, object={object_name} exists on {self.name}."
                )
                return True
            else:
                logger.debug(
                    f"No, object={object_name} does not exist on {self.name}."
                )
                return False
        except ValueError:
            logger.error(
                "Something wrong in exist(). Prpbably ssh did not work temporarily."
            )
            logger.error("Checking if the machine is reachable...")
            time.sleep(self.ssh_retry_time)
            if self.is_alive():
                return self.exist(object_name=object_name)
            raise ValueError

    def is_alive(self):
        if self.machine_type == "remote":
            logger.info(f"Checking if the machine {self.name} is reachable...")
            for tt in range(self.ssh_retry_max_num):
                logger.debug(
                    f"is_alive trial {tt + 1}/{self.ssh_retry_max_num}"
                )
                command = f"ssh {self.username}@{self.ip} 'ls -la > /dev/null'; echo $?"
                # command = f"ssh nazo-computer 'ls -la > /dev/null'; echo $?"
                logger.debug(f"command = {command}")
                proc = subprocess.run(
                    command, shell=True, stdout=PIPE, stderr=PIPE, text=True
                )
                # logger.debug(proc.stdout)
                # logger.debug(proc.stderr)
                if int(proc.stdout) == 0:
                    logger.info(f"{self.name} is alive!!")
                    return True
                else:
                    logger.info(f"{self.name} is not alive!!")
                    logger.info(f"Waiting for {self.ssh_retry_time} sec...")
                    time.sleep(self.ssh_retry_time)
            logger.warning(
                f"Trial exceeds the max num = {self.ssh_retry_max_num}"
            )
            return False
        else:
            return True


class Machines_handler:
    def __init__(
        self,
        client_machine_name: str,
        server_machine_name: str,
        safe_mode: bool = False,
    ):

        self.client_machine = Machine(client_machine_name)
        self.server_machine = Machine(server_machine_name)
        self.safe_mode = safe_mode
        logger.debug(self.client_machine)
        logger.debug(self.server_machine)

        if not self.client_machine.is_alive():
            logger.error(f"client machine {self.client_machine} is dead.")
            raise ConnectionError
        if not self.server_machine.is_alive():
            logger.error(f"server machine {self.server_machine} is dead.")
            raise ConnectionError

    # data transfer class
    def put(
        self,
        from_file: str,
        to_file: str,
        include_list: Optional[list] = None,
        exclude_list: Optional[list] = None,
        dryrun_flag: bool = False,
        delete_flag: bool = False,
        bwlimit: int = 1000,
    ):
        if include_list is None:
            include_list = []
        if exclude_list is None:
            exclude_list = []
        self.object_transfer(
            from_machine=self.client_machine,
            from_object=from_file,
            to_machine=self.server_machine,
            to_object=to_file,
            dir_transfer=False,
            include_list=include_list,
            exclude_list=exclude_list,
            dryrun_flag=dryrun_flag,
            delete_flag=delete_flag,
            bwlimit=bwlimit,
        )

    def put_dir(
        self,
        from_dir: str,
        to_dir: str,
        include_list: Optional[list] = None,
        exclude_list: Optional[list] = None,
        dryrun_flag: bool = False,
        delete_flag: bool = False,
        bwlimit: int = 1000,
    ):
        if include_list is None:
            include_list = []
        if exclude_list is None:
            exclude_list = []
        self.object_transfer(
            from_machine=self.client_machine,
            from_object=from_dir,
            to_machine=self.server_machine,
            to_object=to_dir,
            dir_transfer=True,
            include_list=include_list,
            exclude_list=exclude_list,
            dryrun_flag=dryrun_flag,
            delete_flag=delete_flag,
            bwlimit=bwlimit,
        )

    def get(
        self,
        from_file: str,
        to_file: str,
        include_list: Optional[list] = None,
        exclude_list: Optional[list] = None,
        dryrun_flag: bool = False,
        delete_flag: bool = False,
        bwlimit: int = 1000,
    ):
        if include_list is None:
            include_list = []
        if exclude_list is None:
            exclude_list = []
        self.object_transfer(
            from_machine=self.server_machine,
            from_object=from_file,
            to_machine=self.client_machine,
            to_object=to_file,
            dir_transfer=False,
            include_list=include_list,
            exclude_list=exclude_list,
            dryrun_flag=dryrun_flag,
            delete_flag=delete_flag,
            bwlimit=bwlimit,
        )

    def get_dir(
        self,
        from_dir: str,
        to_dir: str,
        include_list: Optional[list] = None,
        exclude_list: Optional[list] = None,
        dryrun_flag: bool = False,
        delete_flag: bool = False,
        bwlimit: int = 1000,
    ):
        if include_list is None:
            include_list = []
        if exclude_list is None:
            exclude_list = []
        self.object_transfer(
            from_machine=self.server_machine,
            from_object=from_dir,
            to_machine=self.client_machine,
            to_object=to_dir,
            dir_transfer=True,
            include_list=include_list,
            exclude_list=exclude_list,
            dryrun_flag=dryrun_flag,
            delete_flag=delete_flag,
            bwlimit=bwlimit,
        )

    # core object transfer method
    def object_transfer(
        self,
        from_machine: str,
        from_object: str,
        to_machine: str,
        to_object: str,
        dir_transfer: bool = False,
        include_list: Optional[list] = None,
        exclude_list: Optional[list] = None,
        dryrun_flag: bool = False,
        delete_flag: bool = False,
        bwlimit: int = 1000,
    ):
        if include_list is None:
            include_list = []
        if exclude_list is None:
            exclude_list = []

        # check
        assert pathlib.Path(from_object).is_absolute()
        assert pathlib.Path(to_object).is_absolute()

        # isfile(from_file, from_machine) and mkdir(to_file, to_machine)
        if self.safe_mode:
            if dir_transfer:
                assert from_machine.is_dir(dir_name=from_object)
            else:
                assert from_machine.is_file(file_name=from_object)
        logger.debug(
            f"makedir {os.path.dirname(to_object)} on {to_machine.name}"
        )
        to_dir = os.path.dirname(to_object)
        command = f"mkdir -p {to_dir}"
        to_machine.run_command(command)
        if not to_machine.is_dir(dir_name=to_dir):
            logger.error(f"{to_dir} is not created.")
            raise FileNotFoundError

        if (
            from_machine.machine_type == "local"
            and to_machine.machine_type == "local"
        ):
            logger.debug("No data transfer is needed.")
        elif (
            from_machine.machine_type == "local"
            and to_machine.machine_type == "remote"
        ) or (
            from_machine.machine_type == "remote"
            and to_machine.machine_type == "local"
        ):
            # rsync
            if (
                from_machine.machine_type == "local"
                and to_machine.machine_type == "remote"
            ):
                logger.info(
                    f"Transfer data from local machine ({from_machine.name}) to remote machine ({to_machine.name}) using rsync."
                )
                if dir_transfer:  # dir
                    rsync_command = f"rsync --bwlimit {bwlimit} -avz {from_object}/ {to_machine.username}@{to_machine.ip}:{to_object}"
                else:  # file
                    rsync_command = f"rsync --bwlimit {bwlimit} -avz {from_object} {to_machine.username}@{to_machine.ip}:{to_object}"
            else:
                logger.info(
                    f"Transfer data from remote machine ({from_machine.name}) to local machine ({to_machine.name}) using rsync."
                )
                if dir_transfer:  # dir
                    rsync_command = f"rsync --bwlimit {bwlimit} -avz {from_machine.username}@{from_machine.ip}:{from_object}/ {to_object}"
                else:  # file
                    rsync_command = f"rsync --bwlimit {bwlimit} -avz {from_machine.username}@{from_machine.ip}:{from_object} {to_object}"

            logger.info(f"From:: {from_object}")
            logger.info(f"To:: {to_object}")
            if dryrun_flag:
                rsync_command += " -n"
            if len(include_list) > 0:
                # rsync_command += f" --include='*/'"
                for include in include_list:
                    rsync_command += f" --include='{include}'"
                    rsync_command += f" --include='{include}/*'"
                if len(exclude_list) == 0:
                    rsync_command += " --exclude='*'"
            if len(exclude_list) > 0:
                for exclude in exclude_list:
                    rsync_command += f" --exclude='{exclude}'"
            if delete_flag:
                rsync_command += " --delete"
            logger.info(f"rsync_command = {rsync_command}")
            stdout, stderr = Machine.local_run_command(command=rsync_command)
            logger.info("")
            logger.info("==Start:: stdout of the rsync command==")
            logger.info(stdout)
            logger.info("==End:: stdout of the rsync command==")
            logger.info("")

            # special treatment for remote-to-local transfer because it sometimes fails.
            if (
                from_machine.machine_type == "remote"
                and to_machine.machine_type == "local"
            ):
                for tt in range(from_machine.ssh_retry_max_num):
                    logger.debug(
                        f"exist trial {tt + 1}/{from_machine.ssh_retry_max_num}"
                    )
                    if to_machine.exist(object_name=to_object):
                        return
                    logger.error(f"{to_object} is not found!!")
                    logger.info(
                        f"Waiting for {from_machine.ssh_retry_time} sec..."
                    )
                    time.sleep(from_machine.ssh_retry_time)
                    stdout, stderr = Machine.local_run_command(
                        command=rsync_command
                    )
                    logger.info("")
                    logger.info("==Start:: stdout of the rsync command==")
                    logger.info(stdout)
                    logger.info("==End:: stdout of the rsync command==")
                    logger.info("")
                logger.warning(
                    f"Trial exceeds the max num = {from_machine.ssh_retry_max_num}"
                )

        elif (
            from_machine.machine_type == "remote"
            and to_machine.machine_type == "remote"
        ):
            # scp
            logger.info(
                f"Transfer data from remote machine ({from_machine}) to remote machine ({to_machine}) using scp."
            )
            logger.info(f"From {from_object}")
            logger.info(f"To {to_object}")
            logger.warning(
                "dryrun_flag, include_list, and exclude_list options are disabled for a remote-remote data transfer"
            )
            if dir_transfer:  # dir
                scp_command = f"mkdir -p {to_object}"
                logger.info(f"scp_command = {scp_command}")
                Machine.local_run_command(command=scp_command)
                scp_command = f"scp -3r {from_machine.username}@{from_machine.ip}:{from_object}/\* {to_machine.username}@{to_machine.ip}:{to_object}"
                logger.info(f"scp_command = {scp_command}")
                stdout, stderr = Machine.local_run_command(command=scp_command)
                logger.info("")
                logger.info("==Start:: stdout of the scp command==")
                logger.info(stdout)
                logger.info("==End:: stdout of the scp command==")
                logger.info("")
            else:  # file
                scp_command = f"scp -3r {from_machine.username}@{from_machine.ip}:{from_object} {to_machine.username}@{to_machine.ip}:{to_object}"
                logger.info(f"scp_command = {scp_command}")
                stdout, stderr = Machine.local_run_command(command=scp_command)
                logger.info("")
                logger.info("==Start:: stdout of the scp command==")
                logger.info(stdout)
                logger.info("==End:: stdout of the scp command==")
                logger.info("")

        else:
            raise NotImplementedError


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

    machine_handler_test_dir = os.path.join(
        file_manager_test_dir, "machines_handler"
    )
    os.chdir(machine_handler_test_dir)

    # moved to local tests
