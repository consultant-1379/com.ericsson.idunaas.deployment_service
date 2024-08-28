"""This module defines the custom exceptions to be thrown by deployment_manager."""


class Error(Exception):
    """The base class for exceptions in deployment_manager."""


class WorkdirError(Error):
    """The base class for exception in workdir."""


class WorkdirNotMountedError(WorkdirError):
    """Exception raised when workdir is not mounted."""


class WorkdirNotADirectoryError(WorkdirError):
    """Exception raised when workdir is not a directory."""


class KubectlFailedError(Error):
    """Exception raised when a kubectl command fails."""


class AWSError(Error):
    """Exception raised when a kubectl command fails."""
