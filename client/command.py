"""
This module contains all available rpc commands.
"""

import asyncio
import uptime as upt
import os
import platform
from utils import Rpc

import shutil


@Rpc.method
@asyncio.coroutine
def uptime(sid):
    """
    RPC command which returns the current uptime of this client.

    Arguments
    ---------
    sid: int
        Id of the current client

    Returns
    -------
    json consisting of the methodname, uptime and sid
    """
    return {"method": "uptime", "uptime": str(upt.uptime()), "sid": sid}


@Rpc.method
@asyncio.coroutine
def boottime(sid):
    """
    RPC command which returns the boottime of this client. The boottime has to
    following format YYYY-MM-DD hh:mm:ss

    Arguments
    ---------
    sid: int
        Id of the current client

    Returns
    -------
    json consisting of the methodname, boottime and sid
    """
    string_boottime = upt.boottime().strftime("%Y-%m-%d %X")
    return {"method": "boottime", "boottime": string_boottime, "sid": sid}


@Rpc.method
@asyncio.coroutine
def execute(pid, path, arguments):
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
    code = yield from process.wait()

    return {"method": "execute", "code": code, "pid": pid}


@Rpc.method
@asyncio.coroutine
def move_file(fid, sourcePath, destinationPath):
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
    if not isinstance(sourcePath, str):
        raise ValueError("source Path is not a string!")
    if not isinstance(destinationPath, str):
        raise ValueError("destination Path is not a string!")
    else:
        """
        if dest does not exist:
            if the src and dest are a files:
                copy src to dest and rename src
                shutil.copy(src, dest)
            if the src is a  file and the dest is a folder:
                copy src in dest folder
                shutil.copy(src, dest)
            if the src and dest are a folders
                copy the src folder in the dst folder
            if the src is a folder and the dst is a file:
                throw error

        """
        dir = shutil.copy(sourcePath, destinationPath)
        # os.link(sourcePath, destinationPath)

    return {"method": "move_file", "error": os.error, "fid": fid}


@Rpc.method
@asyncio.coroutine
def shutdown():
    """
    shuts down the system
    """
    if platform.system() == "Windows":
        os.system("shutdown -s -t 0")
    else:
        os.system("shutdown -h now")