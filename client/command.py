"""
This module contains all available rpc commands.
"""

import asyncio
import os
import platform
import subprocess
import errno
import hashlib

from pathlib import PurePath

from utils import Rpc
import utils.rpc


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
def hash_file(path):
    """
    Generates a hash string from a given file.

    Parameters
    ----------
        path: str
            A path to a file.

    Returns
    -------
        A str which contains the hash in hex encoding

    Exceptions
    ----------
        ValueError: if the path does not point to a file
    """
    md5 = hashlib.md5()

    with open(path, 'rb') as file_:
        while True:
            data = file_.read(65536)
            if not data:
                break
            md5.update(data)

    return "{}".format(md5.hexdigest())


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
def move_file(source_path, destination_path, backup_ending):
    """
    Function
    --------
    Links and renames a given file to a given destination.
    If the file already exists it will create a BACKUP.

    Arguments
    ---------
    source_path: string
        Represents a valid path to an existing file.
    destination_path: string
        Represents a valid path to the desired destination.
        The file will be renamed and linked to that destination

    Returns
    -------
    ValueError: -
        If source or destination are not strings.

    FileExistsError: -
        If this function is called with BACKUP files in destination
        and the destionation file already exists.

    NotADirectoryError: -
        If the function is called with source as a folder and destination
        as a file.

    FileNotFoundError: -
        If no source is given or the path is invalid.
    """

    if not isinstance(source_path, str):
        raise ValueError("source path is not a string!")
    if not isinstance(destination_path, str):
        raise ValueError("destination path is not a string!")
    if not isinstance(backup_ending, str):
        raise ValueError("Backup file ending is not a string!")
    else:
        source_path = os.path.abspath(source_path)
        destination_path = os.path.abspath(destination_path)
        # File ending of backup files
        backup_file_ending = backup_ending

        if not os.path.exists(source_path):
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                source_path,
            )

        # source is file
        if os.path.isfile(source_path):
            source_file = os.path.basename(source_path)

            if os.path.isdir(destination_path):
                # destination is folder
                destination_path = os.path.join(destination_path, source_file)

            # destination file with name of source exists
            if os.path.isfile(destination_path):
                # Backup file name already exists
                backup_file_name = destination_path + backup_file_ending

                if os.path.exists(backup_file_name):
                    raise FileExistsError(
                        errno.EEXIST,
                        os.strerror(errno.EEXIST),
                        backup_file_name,
                    )
                else:
                    print("Moved to BACKUP")
                    # move old file to backup
                    os.rename(destination_path, backup_file_name)

            # finally link source to destination
            os.link(source_path, destination_path)

            return hash_file(destination_path)
        else:
            raise ValueError(
                "Moving a directory is not supported. ({})".format(
                    source_path))


@Rpc.method
@asyncio.coroutine
def restore_file(source_path, destination_path, backup_ending, hash_value):
    """
    Function
    --------
    Restore the BACKUP files created by move_file to their previous state.

    Arguments
    ---------
    path: string
        Path to the File or Directory to be restored.

    Returns
    -------
    ValueError: -
        If path is not a string.

    FileNotFoundError: -
        Wrong path to file or file does not end with BACKUP ending.
        Or if the file without ending is not a link or directory.
    """
    if not isinstance(source_path, str):
        raise ValueError("source Path is not a string!")
    if not isinstance(destination_path, str):
        raise ValueError("destination Path is not a string!")
    if not isinstance(backup_ending, str):
        raise ValueError("Backup file ending is not a string!")
    if not isinstance(hash_value, str):
        raise ValueError("Hash Value is not a string!")
    else:
        source_path = os.path.abspath(source_path)
        destination_path = os.path.abspath(destination_path)

        backup_path = destination_path + backup_ending

        if not os.path.exists(destination_path):
            if os.path.exists(backup_path):
                os.rename(backup_path, destination_path)

            return None

        hash_gen = hash_file(destination_path)

        if hash_value != hash_gen:
            # TODO: verify

            # if the hash values do not match then
            # check if the source file was changed
            # if the source file was changed but
            # the files are still linked then proceed.
            hash_value = hash_file(source_path)

        if hash_value == hash_gen:
            os.remove(destination_path)
            if os.path.exists(backup_path):
                os.rename(backup_path, destination_path)
        else:
            raise ValueError(
                "The file {} was changed while it was replaced. Remove it yourself.".
                format(destination_path))

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
