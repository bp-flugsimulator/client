"""
This script is used to install all requirements listed in requirements.txt from
./libs. If a library is not present, use the flag "--update" to download the
system specific version from the internet into ./libs and use the flag "--upgrade"
for install.

Example
-------
    $python install.py --update
    $python install.py --upgrade
"""

from sys import stderr, argv
from platform import system, architecture
from distutils.version import LooseVersion

import os
import pip
import argparse


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
    for file in os.listdir('libs'):
        if lib_file in file:
            yield file


def install_local(lib_name):
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
    args = [
        'install',
        lib_name,
        '--no-index',
        '--find-links',
        'file://' + os.getcwd() + '/libs',
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
            os.remove(os.path.join('libs', file))
            print('removed ', file)

    if pip.main(['download', lib_name, '-d', './libs']) != 0:
        raise Exception('could not download ' + lib_name)


if __name__ == "__main__":
    # set up argument parser
    parser = argparse.ArgumentParser(
        description='Uptdates and installs packages needed for the client.')
    parser.add_argument(
        '--upgrade',
        help='installs all packages from ./libs',
        action='store_const',
        const=True)
    parser.add_argument(
        '--update',
        help='downloads all packages from requirements.txt to ./libs',
        action='store_const',
        const=True)

    args = parser.parse_args()

    if args.update:
        # from requirements.txt in ./libs
        if len(argv) > 1 and argv[1] == '--update':
            with open('requirements.txt') as requirements:
                for library in requirements:
                    download(library)

    # update pip to local file
    if args.upgrade:
        if LooseVersion(pip.__version__) < LooseVersion('8.0.0'):
            install_local('pip')

        # install wheel
        install_local('wheel')

        # on windows install pypiwin32
        if system() == 'Windows':
            install_local('pypiwin32')
        elif system() == 'Linux':
            if architecture()[0] != '64bit':
                stderr.write(architecture()[0] +
                             ' is not officially supported but may work\n')
        else:
            stderr.write(
                system() + ' is not officially supported but may work\n')

        # install all other dependencies
        with open('requirements.txt') as requirements:
            for library in requirements:
                if 'git+https://github.com/' in library:
                    generator = git_to_filename(library)
                    pip.main([
                        'install',
                        '--upgrade',
                        '--force-reinstall',
                        os.path.join(os.getcwd(), 'libs', next(generator)),
                    ])
                else:
                    install_local(library),
