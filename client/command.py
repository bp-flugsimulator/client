"""
This module contains all available rpc commands.
"""

import asyncio
import os
import platform
import subprocess

from utils import Rpc


@Rpc.method
@asyncio.coroutine
def online():
    """
    Function that can be used by the master to
    determine if the slave is online
    """
    pass


@Rpc.method
@asyncio.coroutine
def execute(path, arguments):
    """
    Executes a subprocess and returns the exit code.

    Arguments
    ---------
    path: string
        Represents a valid path to an existing program.
    arguments: string[]
        which will be the arguments for the program.
    pid: int
        The ID from the master table.

    Returns
    -------
    Method name, exit code of the process and the pid from the master table.
    A negative value -N indicates that the child was terminated by signal N
    (Unix only).
    """
    if not isinstance(path, str):
        raise ValueError("Path to program is not a string.")

    if not isinstance(arguments, list):
        raise ValueError("Arguments is not a list.")
    else:
        for arg in arguments:
            if not isinstance(arg, str):
                raise ValueError("Element in arguments is not a string.")

    process = yield from asyncio.create_subprocess_exec(*([path] + arguments))

    try:
        code = yield from process.wait()
        return code
    except asyncio.CancelledError:
        process.terminate()
        yield from process.wait()
        return 'Process got canceled and returned {}.'.format(
            process.returncode)


@Rpc.method
@asyncio.coroutine
def move_file(source_path, destination_path):
    """
    Moves and renames a given file to a given destination.

    Arguments
    ---------
    fid: int
        the file ID from the master table.
    sourcePath: string
        Represents a valid path to an existing file.
    destinationPath: string
        Represents a valid path to the desired destination.
        The file will be renamed and linked to that destination

    Returns
    -------
    Method name, error of the process and the fid from the master table.
    """
    if not isinstance(source_path, str):
        raise ValueError("source path is not a string!")
    if not isinstance(destination_path, str):
        raise ValueError("destination path is not a string!")
    else:
        os.link(source_path, destination_path)


@Rpc.method
@asyncio.coroutine
def shutdown():
    """
    shuts down the system
    """
    if platform.system() == "Windows":
        subprocess.call(['shutdown', '-s', '-t', '0'])
    else:
        subprocess.call(['shutdown', '-h', 'now'])
