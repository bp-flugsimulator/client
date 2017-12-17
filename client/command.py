"""
This module contains all available rpc commands.
"""

import asyncio
import uptime as upt
from utils import Rpc


@Rpc.method
def uptime(sid):
    """
    RPC command which returns the current uptime of
    this client.

    Arguments
    ---------
        sid: Id of the current client

    Returns
    -------
        uptime and sid
    """
    return {"uptime": str(upt.uptime()), "sid": sid}


@Rpc.method
def boottime(sid):
    """
    RPC command which returns the boottime of
    this client.

    Arguments
    ---------
        sid: Id of the current client

    Returns
    -------
        boottime and sid
    """
    return {"boottime": str(upt.boottime()), "sid": sid}


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
        Exit code of the process and the pid from the master table.
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

    return {"code": code, "pid": pid}
