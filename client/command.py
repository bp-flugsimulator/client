"""
This module contains all available rpc commands.
"""

import asyncio
import os
import platform
import subprocess
import signal
import shutil

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

    if platform.system() == "Windows":
        process = yield from asyncio.create_subprocess_exec(
            *([path] + arguments),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        process = yield from asyncio.create_subprocess_exec(
            *([path] + arguments))

    try:
        code = yield from process.wait()
        return code
    except asyncio.CancelledError:
        if platform.system() == "Windows":
            process.send_signal(signal.CTRL_C_EVENT)
        else:
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
        raise ValueError("source Path is not a string!")
    if not isinstance(destination_path, str):
        raise ValueError("destination Path is not a string!")
    else:
        """
        Differentiate between file and folder:
        dest.ending = file
        dest        = folder
        ---------------------
        Logic of copy Program:
        ---------------------
        if dest = src:
            return
        if dest is folder:
            if dest does not exist:
                ? error invalid Path ?
                ? if parent folder of dest exists:
                    create folder -> (dest exists)
                else (no parent of dest):
                    error invalid Path ?
            else (dest exists):
                if src is file:
                    copy src file in dest folder
                if src is folder:
                    ? replace src folder with dest folder ?
                    ? place src folder in dest folder ?
                else
                    error invalid src Path
        if dest is file:
            if dest does not exist:
                rename and copy src to dest
            else (dest exists):
                replace dest with src
        else:
            eror invalid dest Path
        """
        if source_path == destination_path:
            return {"method": "move_file"}

        for src_dir, dirs, files in os.walk(source_path):
            dst_dir = src_dir.replace(source_path, destination_path, 1)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    os.rename(dst_file, dst_dir + ".FSIM_BACKUP")
                shutil.move(src_file, dst_dir)

    return {"method": "move_file", "error": os.error}


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
