"""
This script is used to install all requirements listed in requirements.txt
from ./libs. If a library is not present, use the flag "--update" to download
the system specific version from the internet into ./libs and use the flag
"--upgrade" for install.

Example
-------
    $python install.py --download-packages
    $python install.py --download-client 127.0.0.1:4242
"""
from distutils.version import LooseVersion

from platform import system, architecture
from os import listdir, remove, mkdir, getcwd
from os.path import join
from sys import stderr

from json import loads

from argparse import ArgumentParser

from urllib.request import urlretrieve

from shutil import unpack_archive, rmtree

import pip
import sys


class Config:
    """
    Class that represents the config file
    """

    def __init__(self, download_c=None, download_p=False):
        self.__download_client = download_c
        self.__download_packages = download_p

    @classmethod
    def parse(cls):
        """
        Parses 'config.json' and returns a Config object

        Return
        ------
        Config:
            a Config object based on 'config.json'
        """
        try:
            with open('config.json') as config_file:
                data = config_file.read()
                json = loads(data)
                return cls(json['download_client'], json['download_packages'])
        except FileNotFoundError:
            return cls()

    @property
    def download_client(self):
        """
        Getter for __download_client

        Returns
        -------
        str:
            address of the server from where the client gets downloaded
        """
        return self.__download_client

    @property
    def download_packages(self):
        """
        Getter for __download_client

        Returns
        -------
        bool:
            True if packages will get downloaded otherwise false
        """
        return self.__download_packages


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
        # normal archive
        if lib_file in file:
            yield file
        # wheel file
        elif lib_file.replace('-', '_') in file:
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


def download_client(address):
    """
    Downloads client files from the given address.

    Parameter
    ---------
    address: str
        address of the server
    """
    URL = 'http://' + address + '/static/downloads/client.zip'

    print('downloading update from ', URL)
    (file_name, _) = urlretrieve(URL, filename="client.zip")

    print('clear lib folder')
    rmtree(join(getcwd(), 'libs'))
    mkdir(join(getcwd(), 'libs'))

    print('update files')
    unpack_archive(file_name)
    remove(file_name)


def download_library(lib_name):
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
        '--download-packages',
        help='downloads all packages from requirements.txt to ./libs',
        action='store_const',
        const=True)
    PARSER.add_argument(
        '--download-client',
        help='updates the client from the given server',
        metavar=('IP:PORT'),
        type=str)

    ARGS = PARSER.parse_args()

    CONFIG = Config.parse()


    if not (3 == sys.version_info.major and  4 <= sys.version_info.minor <= 6):
        raise Exception('only python 3.4 to 3.6 is supported, currently running ' + str(sys.version))

    # update pip to local file
    if LooseVersion('10.0.0') < LooseVersion(pip.__version__) < LooseVersion('8.0.0'):
        if pip.main([
                'install', '--upgrade', 'pip', '--no-index', '--find-links',
                'file://' + os.getcwd() + '/libs'
        ]) != 0:
            raise Exception('could not install pip from file')



    # select requirements file
    if system() == 'Windows':
        REQUIREMENTS_FILE = 'win_requirements.txt'
    elif system() == 'Linux':
        if architecture()[0] == '64bit':
            REQUIREMENTS_FILE = 'linux_requirements.txt'
        else:
            stderr.write(architecture()[0] +
                         ' is not officially supported but may work\n')
            REQUIREMENTS_FILE = 'linux_requirements.txt'
    else:
        stderr.write(system() + ' is not officially supported but may work\n')

    if ARGS.download_client:
        download_client(ARGS.download_client)
    elif CONFIG.download_client:
        download_client(CONFIG.download_client)

    if ARGS.download_packages or CONFIG.download_packages:
        with open(REQUIREMENTS_FILE) as requirements:
            for library in requirements:
                download_library(library)

    with open(REQUIREMENTS_FILE) as requirements:
        for library in requirements:
            install(library)
