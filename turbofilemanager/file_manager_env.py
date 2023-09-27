#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

# python modules
import os
import sys

# set logger
from logging import getLogger, StreamHandler, Formatter

logger = getLogger("file-manager").getChild(__name__)

# file-manager related path lists
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
file_manager_source_dir = os.path.abspath(
    os.path.dirname(os.path.abspath(__file__))
)
file_manager_root = os.path.abspath(
    os.path.join(file_manager_source_dir, "../")
)
file_manager_test_dir = os.path.join(file_manager_root, "tests")
file_manager_config_dir = os.path.join(
    os.path.abspath(os.environ["HOME"]), "turbofilemanager_config"
)
machine_handler_env_dir = os.path.join(
    file_manager_config_dir, "machine_handler_env"
)
job_manager_env_dir = os.path.join(file_manager_config_dir, "job_manager_env")
machine_handler_env_template_dir = os.path.join(
    file_manager_source_dir, "template", "machine_handler_env"
)
job_manager_env_template_dir = os.path.join(
    file_manager_source_dir, "template", "job_manager_env"
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

    logger.info(file_manager_source_dir)
    logger.info(file_manager_root)
    logger.info(job_manager_env_dir)
    
    # moved to local tests