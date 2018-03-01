"""
Some shorthand functions which will be used in command.py
"""

import os
import hashlib
import errno

import utils.typecheck as uty
import utils.path as up

PATH_TYPE_SET = ['file', 'dir']


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
    uty.ensure_type("source_path", source_path, str)
    uty.ensure_type("destination_path", destination_path, str)
    uty.ensure_type("backup_ending", backup_ending, str)
    uty.ensure_type("PATH_TYPE_SET", PATH_TYPE_SET, list)

    if not source_type in PATH_TYPE_SET:
        raise ValueError(
            "The source_type has to be one of {}".format(PATH_TYPE_SET))
    if not destination_type in PATH_TYPE_SET:
        raise ValueError(
            "The destination_type has to be one of {}".format(PATH_TYPE_SET))

    source_path = up.remove_trailing_path_seperator(source_path)
    destination_path = up.remove_trailing_path_seperator(destination_path)

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
