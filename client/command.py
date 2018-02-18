"""
This module contains all available rpc commands.
"""

import asyncio
import os
import sys
import platform
import subprocess
import errno
import hashlib
import psutil

from pathlib import PurePath
from functools import reduce

from utils import Rpc
import utils.rpc

from .logger import LOGGER


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
def enable_logging(uuid):
    yield from LOGGER.program_loggers[uuid].enable_remote()


@Rpc.method
@asyncio.coroutine
def disable_logging(uuid):
    yield from LOGGER.program_loggers[uuid].disable_remote()


@Rpc.method
@asyncio.coroutine
def execute(own_uuid, path, arguments):
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

    misc_file_name = '{}-{}'.format(PurePath(path).parts[-1], own_uuid)
    misc_file_path = os.path.join(LOGGER.logdir, misc_file_name)

    LOGGER.add_program_logger(own_uuid, misc_file_name + '.log', 1048576)
    PROGRAM_LOGGER = LOGGER.program_loggers[own_uuid]
    log_task = asyncio.get_event_loop().create_task(PROGRAM_LOGGER.run())

    try:
        if platform.system() == 'Windows':
            with open(misc_file_path + '.bat', mode='w') as execute_file:
                execute_file.write('call {path} {args}'.format(
                    path=('"' + path + '"') if ' ' in path else path,
                    args=reduce(lambda r, l: r + ' ' + l, arguments, ''),
                ))
                execute_file.write('{}@echo off'.format(os.linesep))
                execute_file.write('{}echo %errorlevel% > {}.exit'.format(
                    os.linesep, misc_file_path))

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 6

            # TODO 2>&1 blocks :() the input
            command = """call {misc_file_path}.bat 2>&1 | {python} {tee} --port {port}""".format(
                python=sys.executable,
                tee=os.path.join(os.getcwd(), 'applications', 'tee.py'),
                misc_file_path=misc_file_path,
                port=PROGRAM_LOGGER.port,
            )

            print(command)

            process = yield from asyncio.create_subprocess_exec(
                *['cmd.exe', '/c', command],
                cwd=str(PurePath(path).parent),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=startupinfo)
        else:
            command = """({path} {args}) 2>&1 | {python} {tee} --port {port}""".format(
                path=path,
                args=reduce(lambda r, l: r + ' ' + l, arguments, ''),
                python=sys.executable,
                tee=os.path.join(os.getcwd(), 'applications', 'tee.py'),
                misc_file_path=misc_file_path,
                port=PROGRAM_LOGGER.port,
            )

            print(command)

            with open(misc_file_path + '.sh', mode='w') as execute_file:
                execute_file.write('#!/bin/bash' + os.linesep)
                execute_file.write(command + os.linesep)
                execute_file.write('echo ${PIPESTATUS[0]} > ' +
                                   misc_file_path + '.exit' + os.linesep)

            mode = os.stat(misc_file_path + '.sh').st_mode
            mode |= (mode & 0o444) >> 2  # copy R bits to X
            os.chmod(misc_file_path + '.sh', mode)

            process = yield from asyncio.create_subprocess_exec(
                misc_file_path + '.sh',
                cwd=str(PurePath(path).parent),
            )

        yield from asyncio.wait(
            {process.wait(), log_task},
            return_when=asyncio.ALL_COMPLETED,
        )

    except asyncio.CancelledError:

        def children():
            if platform.system() == 'Windows':
                for child in psutil.Process(process.pid).children():
                    for grandchild in child.children(recursive=True):
                        yield grandchild
            else:
                for child in psutil.Process(
                        process.pid).children(recursive=True):
                    if child.pid != process.pid and child.pid != PROGRAM_LOGGER.pid:
                        yield child

        for child in children():
            child.terminate()
            print('terminated: {}'.format(child))

        _, pending = yield from asyncio.wait({process.wait()}, timeout=3)

        if pending:
            for child in children():
                child.kill()
                print('killed: {}'.format(child))

            yield from asyncio.wait(
                {process.wait(), log_task},
                return_when=asyncio.ALL_COMPLETED,
            )

    if platform.system() == 'Windows':
        os.remove(misc_file_path + '.bat')
    else:
        os.remove(misc_file_path + '.sh')

    with open(misc_file_path + '.exit') as log_file:
        return log_file.readlines()[0].rstrip()


@Rpc.method
@asyncio.coroutine
def get_log(target_uuid):
    log = LOGGER.program_loggers[target_uuid].get_log()
    return {'log': log.decode(), 'uuid': target_uuid}


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
