""" This module handles reading and writing into stage log """

import os
from aws_deployment_manager import constants

DELIMITER = "::"


def write_to_stage_log(log_path, stage, state):
    """
    Updates stage log with new phase and state
    :param log_path: Path to stage log file
    :param stage: Stage Name
    :param state: State of phase (started/finished)
    :return: Nothing. Throws exception in case of any failure
    """

    if state not in constants.VALID_STATES:
        raise Exception("Invalid state {0} passed for stage {1}".format(state, stage))

    line = DELIMITER.join([stage, state])
    with open(log_path, "a") as file:
        file.write(line)
        file.write("\n")


def get_all_stages(log_path):
    """
    Reads stage log and returns latest state for each stage
    :param log_path: Path to stage log file
    :return: Dict with key as stage and latest state
    """
    stage_map = {}

    if not os.path.exists(log_path):
        return stage_map

    with open(log_path, "r") as file:
        lines = file.readlines()

    for line in lines:
        if line.strip():
            temp = line.strip().split(DELIMITER)
            stage = temp[0]
            state = temp[1]
            if state in constants.VALID_STATES:
                stage_map[stage] = state

    return stage_map


def get_stage(log_path, stage_name):
    """
    Reads stage log and return latest state for given stage
    :param log_path: Path to stage log file
    :param stage_name: Name of stage
    :return: Stage State (started/finished). If stage does not exist, None is returned
    """
    if not os.path.exists(log_path):
        return None

    stage_map = {}

    with open(log_path, "r") as file:
        lines = file.readlines()

    for line in lines:
        if line:
            temp = line.split(DELIMITER)
            stage = temp[0]
            state = temp[1]
            stage_map[stage] = state

    if stage_name in stage_map:
        return stage_map[stage_name]

    return None
