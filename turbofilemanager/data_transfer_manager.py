# -*- coding: utf-8 -*-
import os

# define logger
from logging import getLogger, StreamHandler, Formatter

# file-manager modules
from turbofilemanager.machine_handler import Machine, Machines_handler
from turbofilemanager.file_manager_env import file_manager_test_dir

logger = getLogger("file-manager").getChild(__name__)

# default bwlimit
bwlimit_default = 30000  # KBytes

class Data_transfer:
    def __init__(
        self,
        local_machine_name: str,
        client_machine_name: str,
        server_machine_name: str,
        safe_mode: bool = False,
        # bwlimit=1000
    ):

        self.local_machine = Machine(local_machine_name)
        self.client_machine = Machine(client_machine_name)
        self.server_machine = Machine(server_machine_name)
        self.machine_handler = Machines_handler(
            client_machine_name=client_machine_name,
            server_machine_name=server_machine_name,
        )
        self.safe_mode = safe_mode
        # self.bwlimit = bwlimit
        # logger.warning(f"bwlimit in the rsync is set {self.bwlimit} KBytes = {int(self.bwlimit*8/10**3)} Mbps")
        # logger.warning(f"You should use a smaller value if rsync fails frequently.")

    def put_objects(
        self,
        from_objects=[],
        include_list=[],
        exclude_list=[],
        dryrun_flag=False,
        delete_flag=False,
    ):

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

        if len(from_objects) == 0:
            logger.debug("from_objects is not specified")
            logger.info(
                "All the files and dirs in the current directory will be rsynced."
            )
            local_current_dir = os.path.abspath(os.getcwd())

            if not (
                self.client_machine.machine_type == "local"
                and self.server_machine.machine_type == "local"
            ):
                if local_home not in local_current_dir:
                    logger.error(
                        "server-client_manager.py works only in the local_home dir."
                    )
                    raise ValueError
            client_dir = local_current_dir.replace(local_home, client_home)
            server_dir = local_current_dir.replace(local_home, server_home)
            logger.debug(client_dir)
            logger.debug(server_dir)
            self.machine_handler.put_dir(
                from_dir=client_dir,
                to_dir=server_dir,
                include_list=include_list,
                exclude_list=exclude_list,
                dryrun_flag=dryrun_flag,
                delete_flag=delete_flag,
                bwlimit=bwlimit_default,
            )

        else:
            logger.debug("from_objects is specified")
            logger.info(
                "The files and dirs in the objects will be rsynced to the corresponding remote dir."
            )

            for object in from_objects:
                object_abs = os.path.abspath(object)
                if local_home not in object_abs:
                    logger.error(
                        "server-client_manager.py works only in the local_home dir."
                    )
                    raise ValueError
                from_object = object_abs.replace(local_home, client_home)
                to_object = object_abs.replace(local_home, server_home)
                if self.client_machine.is_file(file_name=from_object):
                    self.machine_handler.put(
                        from_file=from_object,
                        to_file=to_object,
                        include_list=include_list,
                        exclude_list=exclude_list,
                        dryrun_flag=dryrun_flag,
                        delete_flag=delete_flag,
                        bwlimit=bwlimit_default,
                    )
                else:  # isdir(from_object)
                    self.machine_handler.put_dir(
                        from_dir=from_object,
                        to_dir=to_object,
                        include_list=include_list,
                        exclude_list=exclude_list,
                        dryrun_flag=dryrun_flag,
                        delete_flag=delete_flag,
                        bwlimit=bwlimit_default,
                    )

    def get_objects(
        self,
        from_objects=[],
        include_list=[],
        exclude_list=[],
        dryrun_flag=False,
        delete_flag=False,
    ):

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

        logger.info(f"client_dir_root={client_home}")
        logger.info(f"server_dir_root={server_home}")

        local_current_dir = os.path.abspath(os.getcwd())
        if not (
            self.client_machine.machine_type == "local"
            and self.server_machine.machine_type == "local"
        ):
            if local_home not in local_current_dir:
                logger.error(
                    "server-client_manager.py works only in the local_home dir."
                )
                raise ValueError
            else:
                client_dir = local_current_dir.replace(local_home, client_home)
                server_dir = local_current_dir.replace(local_home, server_home)

                if len(from_objects) == 0:
                    logger.info("from objects is not specified")
                    logger.info(
                        "All the files and dirs in the corresponding remote dir. will be rsynced."
                    )
                    self.machine_handler.get_dir(
                        from_dir=server_dir,
                        to_dir=client_dir,
                        include_list=include_list,
                        exclude_list=exclude_list,
                        dryrun_flag=dryrun_flag,
                        delete_flag=delete_flag,
                        bwlimit=bwlimit_default,
                    )

                else:
                    logger.info("remote_objects_list is specified")
                    logger.info(
                        "The files and dirs in the remote_objects_list will be rsynced from the corresponding remote dir."
                    )

                    for object in from_objects:
                        from_object = os.path.join(server_dir, object)
                        if not self.server_machine.exist(
                            object_name=from_object
                        ):
                            logger.error(
                                f"{from_object} does not exist on server_machine"
                            )
                            raise FileNotFoundError
                        to_object = from_object.replace(
                            server_home, client_home
                        )
                        if self.server_machine.is_file(file_name=from_object):
                            self.machine_handler.get(
                                from_file=from_object,
                                to_file=to_object,
                                include_list=include_list,
                                exclude_list=exclude_list,
                                dryrun_flag=dryrun_flag,
                                delete_flag=delete_flag,
                                bwlimit=bwlimit_default,
                            )
                        else:  # mysftp.is_dir(remote_dir=from_object):
                            self.machine_handler.get_dir(
                                from_dir=from_object,
                                to_dir=to_object,
                                include_list=include_list,
                                exclude_list=exclude_list,
                                dryrun_flag=dryrun_flag,
                                delete_flag=delete_flag,
                                bwlimit=bwlimit_default,
                            )


if __name__ == "__main__":
    from logging import getLogger

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

    # moved to test