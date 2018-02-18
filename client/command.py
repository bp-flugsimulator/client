"""
This module contains all available rpc commands.
"""

import asyncio
import os
import platform
import subprocess
import errno
import shutil
import hashlib

from pathlib import PurePath

from utils import Rpc, Command, Status
import utils.rpc

PATH_TYPE_SET = ['file', 'dir']


class Helper:
    """
    Stores all functions which are helper functions.
    """
    methods = []
    function = utils.rpc.method_wrapper(methods)

    @staticmethod
    def get(fun):
        """
        Searches for a function with a given name.

        Arguments
        ---------
            fun: str, function name

        Returns
        -------
            Function Handle or None
        """
        for f in Helper.methods:
            if f.__name__ == fun:
                return f

        return None


@Helper.function
def remove_trailing_path_seperator(path):
    """
    If the last character is a path seperator, then it will be removed.

    Arguments
    ----------
        path: string

    Returns
    -------
        string
    """
    if path and path[-1] == os.path.sep:
        return path[:-1]
    else:
        return path


@Helper.function
def hash_file(path):
    """
    Generates a hash string from a given file.

    Parameters
    ----------
        path: str
            A path to a file.

    Returns
    -------
        A string with an MD5 hash

    Exceptions
    ----------
        ValueError: if the path does not point to a file
    """
    if not os.path.isfile(path):
        raise ValueError("The given path `{}` is not a file.".format(path))

    md5 = hashlib.md5()

    with open(path, 'rb') as file_:
        while True:
            data = file_.read(65536)
            if not data:
                break
            md5.update(data)

    return "{}".format(md5.hexdigest())


@Helper.function
def hash_directory(path):
    """
    Retrieves the hash for each file in this directory (recursive) and hashes all the file
    hashes.

    Arguments
    ---------
        path: directory path

    Returns
    -------
        A string with an MD5 hash
    """
    if not os.path.isdir(path):
        raise ValueError(
            "The given path `{}` is not a directory.".format(path))

    md5 = hashlib.md5()

    for root, _, files in os.walk(path):
        for fil in files:
            md5.update(hash_file(os.path.join(root, fil)).encode("utf-8"))

    return "{}".format(md5.hexdigest())


@Helper.function
def filesystem_type_check(
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
):
    """
    Check the types of the shared input of filesystem_move and filesystem_restore.
    """
    if not isinstance(source_path, str):
        raise ValueError("source path is not a string!")
    if not isinstance(destination_path, str):
        raise ValueError("destination path is not a string!")
    if not isinstance(backup_ending, str):
        raise ValueError("Backup file ending is not a string!")
    if not source_type in PATH_TYPE_SET:
        raise ValueError(
            "The source_type has to be one of {}".format(PATH_TYPE_SET))
    if not destination_type in PATH_TYPE_SET:
        raise ValueError(
            "The destination_type has to be one of {}".format(PATH_TYPE_SET))

    source_path = remove_trailing_path_seperator(source_path)
    destination_path = remove_trailing_path_seperator(destination_path)

    source_path = os.path.abspath(source_path)
    destination_path = os.path.abspath(destination_path)

    if not os.path.exists(source_path):
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            source_path,
        )

    # check if source is dir or file (based on source path)
    if source_type == 'dir':
        if not os.path.isdir(source_path):
            raise ValueError(
                "The source path `{}` is not a directory.".format(source_path))
    elif source_type == 'file':
        if not os.path.isfile(source_path):
            raise ValueError(
                "The source path `{}` is not a file.".format(source_path))

    # extract source name from path
    source_file = os.path.basename(source_path)

    # destination is a directory
    if destination_type == 'dir':
        destination_path = os.path.join(destination_path, source_file)

    return (
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
        source_file,
    )


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
        source_file,
    ) = filesystem_type_check(
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
        return hash_directory(destination_path)

    elif source_type == 'file':
        # finally link source to destination
        os.link(source_path, destination_path)
        return hash_file(destination_path)


@Helper.function
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
    if not isinstance(hash_value, str):
        raise ValueError("hash value is not a string!")

    (
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
        source_file,
    ) = filesystem_type_check(
        source_path,
        source_type,
        destination_path,
        destination_type,
        backup_ending,
    )

    backup_path = destination_path + backup_ending

    if os.path.exists(destination_path):

        if source_type == 'file':
            hash_gen = hash_file(destination_path)
        elif source_type == 'dir':
            hash_gen = hash_directory(destination_path)

        if hash_value != hash_gen and os.path.exists(source_path):
            # if the hash values do not match then
            # check if the source file was changed
            # if the source file was changed but
            # the files are still linked then proceed.
            if source_type == 'file':
                hash_value = hash_file(source_path)
            elif source_type == 'dir':
                hash_value = hash_directory(source_path)

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
