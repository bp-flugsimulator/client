"""
This module contains all available rpc commands.
"""

import asyncio
import os
import platform
import subprocess
import shutil
import errno

from pathlib import PurePath

from utils import Rpc, Command, Status
import utils.rpc
import utils.typecheck as uty
import utils.path as up
import client.shorthand as sh


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

    process = yield from asyncio.create_subprocess_exec(
        *([path] + arguments), cwd=str(PurePath(path).parent))

    try:
        code = yield from process.wait()
        return code
    except asyncio.CancelledError:
        if platform.system() == "Windows":
            import psutil
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.terminate()

        process.terminate()
        yield from process.wait()
        return 'Process got canceled and returned {}.'.format(
            process.returncode)


@Rpc.method
@asyncio.coroutine
def chain_execution(commands):
    """
    Executes given commands sequential. If one commands fails all other commands fail
    too.
    """
    result = []
    error = False

    for command in commands:
        try:
            cmd = Command(
                command["method"],
                uuid=command["uuid"],
                **command["arguments"])
        except Exception as err:  #pylint: disable=W0703
            print(err)
            continue

        if error:
            ret = Status(
                Status.ID_ERR,
                {
                    'method':
                    cmd.method,
                    'result':
                    "Could not execute because earlier command was not successful."
                },
                cmd.uuid,
            )

            result.append(dict(ret))
        else:

            try:
                fun = Rpc.get(cmd.method)
                print(dict(cmd))
                ret = yield from asyncio.coroutine(fun)(**cmd.arguments)

                ret = Status(
                    Status.ID_OK,
                    {'method': cmd.method,
                     'result': ret},
                    cmd.uuid,
                )

                result.append(dict(ret))
            except Exception as err:  #pylint: disable=W0703
                ret = Status(
                    Status.ID_ERR,
                    {'method': cmd.method,
                     'result': str(err)},
                    cmd.uuid,
                )

                result.append(dict(ret))
                error = True

    return result


@Rpc.method
@asyncio.coroutine
def filesystem_move(
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
):
    """
    Moves a file from the source to the destination.

    Arguments
    ---------
        source_path: path to the source
        source_type: Type of the source (a directory -> 'dir' or a file -> 'file')
        destination_path: path to the destination
        destination_type: Type of the destination (place it in a directory -> 'dir' or replace it -> 'file')
        backup_ending: the file ending for backup files

    Returns
    -------
        The hash of the source
    """
    (
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
        _,
    ) = sh.filesystem_type_check(
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
    )

    # destination file with name of source exists
    if (source_type == 'dir' and os.path.isdir(destination_path)) or (
            source_type == 'file' and os.path.isfile(destination_path)):

        # Backup file name already exists
        backup_path = destination_path + backup_ending

        if os.path.exists(backup_path):
            raise FileExistsError(
                errno.EEXIST,
                os.strerror(errno.EEXIST),
                backup_path,
            )

        # move old file to backup
        os.rename(destination_path, backup_path)

    elif os.path.exists(destination_path):
        raise ValueError(
            "Expected a {} at `{}`, but did not found one.".format(
                "file"
                if source_type == "file" else "directory", destination_path))

    if source_type == 'dir':
        os.mkdir(destination_path)

        for root, dirs, files in os.walk(source_path):
            # set the prefix from source_path to destination_path
            dest_root = os.path.join(destination_path,
                                     root[len(source_path) + 1:])

            for directory in dirs:
                os.mkdir(os.path.join(dest_root, directory))

            for fil in files:
                os.link(
                    os.path.join(root, fil),
                    os.path.join(dest_root, fil),
                )
        return sh.hash_directory(destination_path)

    elif source_type == 'file':
        # finally link source to destination
        os.link(source_path, destination_path)
        return sh.hash_file(destination_path)


@Rpc.method
@asyncio.coroutine
def filesystem_restore(
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
        hash_value,
):
    """
    Restores a previously moved object.

    Arguments
    ---------
        source_path: path to the source
        source_type: Type of the source (a directory -> 'dir' or a file -> 'file')
        destination_path: path to the destination
        destination_type: Type of the destination (place it in a directory -> 'dir' or
             replace it -> 'file')
        backup_ending: the file ending for backup files

    """
    uty.ensure_type("hash_value", hash_value, str)

    (
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
        _,
    ) = sh.filesystem_type_check(
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
    )

    backup_path = destination_path + backup_ending

    if os.path.exists(destination_path):

        if source_type == 'file':
            hash_gen = sh.hash_file(destination_path)
        elif source_type == 'dir':
            hash_gen = sh.hash_directory(destination_path)

        if hash_value != hash_gen and os.path.exists(source_path):
            # if the hash values do not match then
            # check if the source file was changed
            # if the source file was changed but
            # the files are still linked then proceed.
            if source_type == 'file':
                hash_value = sh.hash_file(source_path)
            elif source_type == 'dir':
                hash_value = sh.hash_directory(source_path)

        if hash_value == hash_gen:
            if source_type == 'dir':
                shutil.rmtree(destination_path)
            elif source_type == 'file':
                os.remove(destination_path)
        else:
            raise ValueError(
                "The {} `{}` was changed while it was replaced. Remove it yourself if you don not need it.".
                format(
                    "file" if source_type == 'file' else 'directory',
                    destination_path,
                ))

    if os.path.exists(backup_path):
        os.rename(backup_path, destination_path)

    return None


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
