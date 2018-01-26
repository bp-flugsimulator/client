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
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=str(PurePath(path).parent),
        )
    else:
        process = yield from asyncio.create_subprocess_exec(
            *([path] + arguments),
            cwd=str(PurePath(path).parent),
        )

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
        raise ValueError("source Path is not a string!")
    if not isinstance(destination_path, str):
        raise ValueError("destination Path is not a string!")
    if not isinstance(backup_ending, str):
        raise ValueError("Backup file ending is not a string!")
    else:
        source_path = os.path.abspath(source_path)
        destination_path = os.path.abspath(destination_path)
        # File ending of backup files
        backup_file_ending = backup_ending

        # source is file
        if os.path.isfile(source_path):
            source_file = os.path.basename(source_path)
            # destination is folder
            if os.path.isdir(destination_path):
                destination_path = os.path.join(destination_path, source_file)
            backup_file_name = destination_path + backup_file_ending
            # destination file with name of source exists
            if os.path.islink(destination_path):
                os.remove(destination_path)
            elif os.path.isfile(destination_path):
                # Backup file name already exists
                if os.path.exists(backup_file_name):
                    raise FileExistsError(
                        errno.EEXIST,
                        os.strerror(errno.EEXIST),
                        backup_file_name,
                    )
                os.rename(destination_path, backup_file_name)
            # finally (rename and) link source to destination
            md5 = hashlib.md5()
            BUF_SIZE = 65536

            os.link(source_path, destination_path)
            with open(destination_path, 'rb') as file_:
                while True:
                    data = file_.read(BUF_SIZE)
                    if not data:
                        break
                    md5.update(data)
            return "{0}".format(md5.hexdigest())

        # # source is folder (NOT POSSIBLE ANYMORE)
        # elif os.path.isdir(source_path):
        #     dst_dir = os.path.join(
        #         destination_path,
        #         os.path.basename(source_path),
        #     )
        #     # destination cant be a file if source is folder
        #     if os.path.isfile(destination_path):
        #         raise NotADirectoryError(
        #             errno.ENOTDIR,
        #             os.strerror(errno.ENOTDIR),
        #             destination_path,
        #         )
        #     if os.path.isdir(dst_dir):
        #         # Backup file name already exits
        #         if os.path.exists(dst_dir + backup_file_ending):
        #             raise FileExistsError(
        #                 errno.EEXIST,
        #                 os.strerror(errno.EEXIST),
        #                 dst_dir + backup_file_ending,
        #             )
        #         os.rename(
        #             dst_dir,
        #             dst_dir + backup_file_ending,
        #         )
        #     for src_dir, _, files in os.walk(source_path):
        #         dest_src = os.path.join(
        #             os.path.basename(destination_path),
        #             os.path.basename(source_path),
        #         )
        #         dst_dir = src_dir.replace(
        #             os.path.basename(source_path),
        #             dest_src,
        #         )
        #         # If source folder does not exist in destination create it.
        #         if not os.path.exists(dst_dir):
        #             os.makedirs(dst_dir)
        #         for file_ in files:
        #             src_file = os.path.join(src_dir, file_)
        #             dst_file = os.path.join(dst_dir, file_)
        #             # link source to destination
        #             os.link(src_file, dst_file)
        else:
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                source_path,
            )


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

        link_path = os.path.join(
            os.path.dirname(destination_path),
            os.path.basename(source_path),
        )
        backup_path = destination_path + backup_ending

        print(backup_path)

        md5 = hashlib.md5()
        BUF_SIZE = 65536

        with open(destination_path, 'rb') as file_:
            while True:
                data = file_.read(BUF_SIZE)
                if not data:
                    break
                md5.update(data)
        hash_gen = "{0}".format(md5.hexdigest())

        if hash_value == hash_gen:
            if os.path.exists(backup_path):
                os.remove(destination_path)
                os.rename(backup_path, destination_path)
            else:
                raise FileNotFoundError(
                    errno.ENOENT,
                    os.strerror(errno.ENOENT),
                    backup_path,
                )
        else:
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                destination_path,
            )


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
