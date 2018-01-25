"""
This script is used to install all requirements listed in requirements.txt
from ./libs. If a library is not present, use the flag "--update" to download
the system specific version from the internet into ./libs and use the flag
"--upgrade" for install.

Example
-------
    $python install.py --update
    $python install.py --upgrade
"""

from platform import system, architecture
from os import listdir, getcwd, remove
from os.path import join
from sys import stderr

from argparse import ArgumentParser

from urllib.request import urlretrieve

from shutil import unpack_archive

import pip


def git_to_filename(git_url):
    """
    translates a git url to a file name

    Parameters
    ----------
    git_url: str
        the url to the git repository

    Returns
    -------
    str:
        name of the file
    """
    lib_file = git_url.replace('git+https://github.com/', '')
    lib_file = lib_file.replace('/', '-')
    lib_file = lib_file.replace('\n', '')
    for file in listdir('libs'):
        if lib_file in file:
            yield file


def install(lib_name):
    """
    Installes a library from a local file in ./libs

    Parameters
    ----------
    lib_name: str
        the name of the library that will be installed

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an Exception if the library can't be installed
    from a local file
    """
    if 'git+https://github.com/' in library:
        file = next(git_to_filename(library))
        if file is None:
            raise Exception('could not install ' + lib_name +
                            ' from file, because file does not exist.')
        else:
            args = [
                'install',
                '--upgrade',
                '--force-reinstall',
                join(getcwd(), 'libs', file),
            ]
    else:
        args = [
            'install',
            lib_name,
            '--no-index',
            '--find-links',
            'file://' + getcwd() + '/libs',
        ]

    if pip.main(args) != 0:
        raise Exception('could not install ' + lib_name + ' from file')


def download(lib_name):
    """
    Downloads a library to ./libs

    Parameters
    ----------
    lib_name: str
        the name of the library that will be downloaded

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an Exception if the library can't be
    downloaded from a local file
    """
    if 'git+https://github.com/' in library:
        for file in git_to_filename(lib_name):
            remove(join('libs', file))
            print('removed ', file)

    if pip.main(['download', lib_name, '-d', './libs']) != 0:
        raise Exception('could not download ' + lib_name)


if __name__ == "__main__":
    # set up argument parser
    PARSER = ArgumentParser(
        description='Updates and installs packages needed for the client.')
    PARSER.add_argument(
        '--upgrade',
        help='installs all packages from ./libs',
        action='store_const',
        const=True)
    PARSER.add_argument(
        '--update',
        help='downloads all packages from requirements.txt to ./libs',
        action='store_const',
        const=True)
    PARSER.add_argument(
        '--update_client',
        help='updates the client from the given server',
        type=str)

    ARGS = PARSER.parse_args()

    if not (ARGS.update or ARGS.upgrade or ARGS.update_client):
        PARSER.print_help()

    # select requirements file
    if system() == 'Windows':
        REQUIREMENTS_FILE = 'win_requirements.txt'
    elif system() == 'Linux':
        if architecture()[0] == '64bit':
            REQUIREMENTS_FILE = 'linux_requirements.txt'
        else:
            stderr.write(architecture()[0] +
                         ' is not officially supported but may work\n')
    else:
        stderr.write(system() + ' is not officially supported but may work\n')

    if ARGS.update_client:
        (file_name, _) = urlretrieve('http://' + str(ARGS.update_client) +
                                     '/static/downloads/client.zip')
        unpack_archive(file_name)

    if ARGS.update:
        with open(REQUIREMENTS_FILE) as requirements:
            for library in requirements:
                download(library)

    if ARGS.upgrade:
        with open(REQUIREMENTS_FILE) as requirements:
            for library in requirements:
                install(library)
