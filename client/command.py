"""
This module contains all available rpc commands.
"""

import asyncio
import os
import sys
import platform
import subprocess
import shutil
import errno
import psutil

from pathlib import PurePath
from functools import reduce

from utils import Rpc, Command, Status
import utils.rpc
import utils.typecheck as uty

from client.logger import LOGGER
from client import shorthand as sh


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
def enable_logging(target_uuid):
    """
    Enables logging over websockets on the path '/logs'

    Arguments
    ---------
    target_uuid: string
        uuid of the command for with logging gets enabled
    """
    yield from LOGGER.program_loggers[target_uuid].enable_remote()


@Rpc.method
@asyncio.coroutine
def disable_logging(target_uuid):
    """
    Disables logging over websockets on the path '/logs'

    Arguments
    ---------
    target_uuid: string
        uuid of the command for with logging gets disabled
    """
    yield from LOGGER.program_loggers[target_uuid].disable_remote()


@Rpc.method
@asyncio.coroutine
def execute(pid, own_uuid, path, arguments):
    """
    Executes a the program with arguments in a new Terminal/CMD window.
    The output of the program gets piped into '/applications/tee.py' and logged
    by a ProgramLogger.

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

    misc_file_name = '{}-{}'.format(PurePath(path).parts[-1],
                                    own_uuid).replace(' ', '')
    misc_file_path = os.path.join(LOGGER.logdir, misc_file_name)

    LOGGER.add_program_logger(pid, own_uuid,
                              sh.escape_path(misc_file_name + '.log'),
                              (1 << 20) * 2)
    PROGRAM_LOGGER = LOGGER.program_loggers[own_uuid]
    log_task = asyncio.get_event_loop().create_task(PROGRAM_LOGGER.run())
    try:
        if platform.system() == 'Windows':
            with open(misc_file_path + '.bat', mode='w') as execute_file:
                execute_file.write('@echo off{}'.format(os.linesep))
                execute_file.write('mode 80,60{}'.format(os.linesep))
                execute_file.write('@echo on{}'.format(os.linesep))
                execute_file.write('call {path} {args}'.format(
                    path=sh.escape_path(path),
                    args=reduce(lambda r, l: r + ' ' + l, arguments, ''),
                ))
                execute_file.write('{}@echo off'.format(os.linesep))
                execute_file.write('{}echo %errorlevel% > {}'.format(
                    os.linesep, sh.escape_path(misc_file_path + '.exit')))

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 6

            command = """call {bat_file_path} 2>&1 | {python} {tee} --port {port}""".format(
                python=sys.executable,
                tee=os.path.join(os.getcwd(), 'applications', 'tee.py'),
                bat_file_path=sh.escape_path(misc_file_path + '.bat'),
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
                path=sh.escape_path(path),
                args=reduce(lambda r, l: r + ' ' + l, arguments, ''),
                python=sys.executable,
                tee=os.path.join(os.getcwd(), 'applications', 'tee.py'),
                port=PROGRAM_LOGGER.port,
            )

            print(command)

            with open(misc_file_path + '.sh', mode='w') as execute_file:
                execute_file.write('#!/bin/bash' + os.linesep)
                execute_file.write(command + os.linesep)
                execute_file.write('echo ${PIPESTATUS[0]} > ' + sh.escape_path(
                    misc_file_path + '.exit') + os.linesep)

            mode = os.stat(misc_file_path + '.sh').st_mode
            mode |= (mode & 0o444) >> 2  # copy R bits to X
            os.chmod(misc_file_path + '.sh', mode)

            if 'DISPLAY' in os.environ and shutil.which('xterm'):
                subprocess_arguments = [
                    'xterm', '-e', sh.escape_path(misc_file_path + '.sh'), '-geometry', '80'
                ]
            else:
                subprocess_arguments = [sh.escape_path(misc_file_path + '.sh')]

            process = yield from asyncio.create_subprocess_exec(
                *subprocess_arguments, cwd=str(PurePath(path).parent))

        yield from asyncio.wait(
            {process.wait(), log_task}, return_when=asyncio.ALL_COMPLETED)

    except asyncio.CancelledError:

        def children():
            if platform.system() == 'Windows':
                for child in psutil.Process(process.pid).children():
                    for grandchild in child.children(recursive=True):
                        yield grandchild
            else:
                for child in psutil.Process(
                        process.pid).children(recursive=True):
                    if (child.pid != process.pid
                            and child.pid != PROGRAM_LOGGER.pid
                            and child.name() != misc_file_name[:15]):
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
                {process.wait(), log_task}, return_when=asyncio.ALL_COMPLETED)

    if platform.system() == 'Windows':
        os.remove(misc_file_path + '.bat')
    else:
        os.remove(misc_file_path + '.sh')

    with open(misc_file_path + '.exit') as log_file:
        return log_file.readlines()[0].rstrip()


@Rpc.method
@asyncio.coroutine
def get_log(target_uuid):
    """
    Returns the current log of the program that is/was executed by a Command
    with the given uuid.

    Arguments
    ---------
    target_uuid: string
        uuid of the command which started the program

    Returns
    -------
    a dictionary containing the log and the uuid
    """
    log = LOGGER.program_loggers[target_uuid].get_log()
    return {'log': log.decode(), 'uuid': target_uuid}


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
                    {
                        'method': cmd.method,
                        'result': ret
                    },
                    cmd.uuid,
                )

                result.append(dict(ret))
            except Exception as err:  #pylint: disable=W0703
                ret = Status(
                    Status.ID_ERR,
                    {
                        'method': cmd.method,
                        'result': str(err)
                    },
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
