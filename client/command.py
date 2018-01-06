"""
This module contains all available rpc commands.
"""

import asyncio
import uptime as upt
import os
from utils import Rpc


@Rpc.method
@asyncio.coroutine
def uptime(sid):
    """
    RPC command which returns the current uptime of this client.

    Arguments
    ---------
        sid: Id of the current client

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
        sid: Id of the current client

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
        path: A string which represents a valid path to an existing program.
        arguments: A list of strings which will be the arguments for the
                     program.
        pid: The ID from the master table.

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
    moves File
    """
    if not isinstance(sourcePath, str):
        raise ValueError("source path is not a string!")
    if not isinstance(destinationPath, str):
        raise ValueError("destination path is not a string!")
    else:
        os.link(sourcePath, destinationPath)

    return {"method": "move_file", "error": os.error, "fid": fid}
