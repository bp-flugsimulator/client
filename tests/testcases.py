"""
This module provides additional test cases for the client library.
"""
#pylint: disable=C0103

import unittest
import os
import asyncio
import shutil
import random
import hashlib
import string

import client.shorthand


def random_string(minimum, maximum):
    """
    Returns a random ASCII sequence between start and end.

    Arguments
    ---------
        start: minimum chars
        end: maximum chars

    Returns
    -------
        random string
    """
    length = random.randint(minimum, maximum)

    return ''.join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase +
                      string.digits) for _ in range(length))


class EventLoopTestCase(unittest.TestCase):
    """
    A TestCase class which provides an event loop, to test async functions.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if os.name == 'nt':
            cls.loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(cls.loop)
        else:
            cls.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls.loop)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.loop.close()


class FileSystemTestCase(EventLoopTestCase):
    """
    A unittest case which provides a filesystem api.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.working_dir = os.path.join(os.getcwd(), "unittest.files.temp")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def setUp(self):
        if os.path.exists(self.working_dir):
            raise AssertionError(
                "Can not start test because the test folder does allready exists."
            )

        os.mkdir(self.working_dir)

    def tearDown(self):
        if not os.path.exists(self.working_dir):
            raise AssertionError(
                "Can not delete test folder (which was create before) because it does not exist anymore. "
            )

        shutil.rmtree(self.working_dir)

    def filesInDir(self):
        """
        Returns a list of files (recursive) within a directory. Every file has a prefix
        based on the path related to the self.working_dir.

        Returns
        -------
            List of strings
        """
        all_files = []

        for root, _, files in os.walk(self.working_dir):
            subtracted = os.path.relpath(root, self.working_dir)

            for fil in files:
                all_files.append(os.path.join(subtracted, fil))

        return all_files

    def dirsInDir(self):
        """
        Returns a list of directories (recursive) within a directory. Every directory has
        a prefix based ont he path related to the self.working_dir.

        Returns
        -------
            List of strings
        """
        dirs = []

        for root, _, _ in os.walk(self.working_dir):
            subtracted = os.path.relpath(root, self.working_dir)

            if not subtracted == '.':
                dirs.append(subtracted)

        return dirs

    def fileHashesInDir(self, path):
        """
        Returns a list with hashes which are generated from the files in that directory.
        """

        path = self.joinPath(path)

        if not os.path.isdir(path):
            raise AssertionError("The path `{}` is no directory.".format(path))

        hashes = []

        for root, _, files in os.walk(path):
            hashes.extend(
                map(lambda f: client.shorthand.hash_file(os.path.join(root, f)),
                    files))

        return hashes

    def assertFilesArePresent(self, *args):
        """
        Asserts that all listed files are in the directory. Use relative paths.

        Exception
        ---------
            AssertionError if a file is not in the directory.

        Arguments
        ---------
            args: list of file paths
        """
        if len(args) < 1:
            raise AssertionError("No files provided.")

        for arg in args:
            if not os.path.isfile(os.path.join(self.working_dir, arg)):
                raise AssertionError(
                    "The file `{}` was not present in the directory `{}`. The following files where present:\n{}".
                    format(
                        arg,
                        self.working_dir,
                        '\n'.join(map(str, self.filesInDir())),
                    ))

    def assertFilesAreNotPresent(self, *args):
        """
        Asserts that all listed files are not in the directory. Use relative paths.

        Exception
        ---------
            AssertionError if a file is in the directory.
        """
        if len(args) < 1:
            raise AssertionError("No files provided.")

        elements = []

        for arg in args:
            if os.path.isfile(os.path.join(self.working_dir, arg)):
                elements.append(arg)

        if elements:
            raise AssertionError(
                "The files `{}` were present in the directory `{}`. The following files where also present:\n{}".
                format(
                    ', '.join(map(str, elements)),
                    self.working_dir,
                    '\n'.join(map(str, self.filesInDir())),
                ))

    def assertDirsArePresent(self, *args):
        """
        Asserts that all listed directories are in the directory. Use relative paths.

        Exception
        ---------
            AssertionError if a directory is not in the directory.

        Arguments
        ---------
            args: List of directory paths
        """
        if len(args) < 1:
            raise AssertionError("No directories provided.")

        for arg in args:
            if not os.path.isdir(os.path.join(self.working_dir, arg)):
                raise AssertionError(
                    "The directory `{}` was not present in the directory `{}`. The following directories where present:\n{}".
                    format(
                        arg,
                        self.working_dir,
                        '\n'.join(map(str, self.dirsInDir())),
                    ))

    def assertDirsAreNotPresent(self, *args):
        """
        Asserts that all listed directory are not in the directory. Use relative paths.

        Exception
        ---------
            AssertionError if a directory is in the directory.

        Arguments
        ---------
            args: List of dir paths
        """
        if len(args) < 1:
            raise AssertionError("No directories provided.")

        elements = []

        for arg in args:
            if os.path.isdir(os.path.join(self.working_dir, arg)):
                elements.append(arg)

        if elements:
            raise AssertionError(
                "The directories `{}` were present in the directory `{}`. The following directories where also present:\n{}".
                format(
                    ', '.join(map(str, elements)),
                    self.working_dir,
                    '\n'.join(map(str, self.dirsInDir())),
                ))

    def assertDirsEqual(self, *rel_args):
        """
        Tests if two directories have the same files if all of the files in both
        directories have the same content.

        dir1 == dir2 and dir1 == dir3 and ... and dir1 == dirN

        Arguments
        ---------
            args: List of directory paths
        """
        if len(rel_args) < 2:
            raise AssertionError("Need two directories to compare.")

        # convert to list to remove elements
        args = list(rel_args)
        item = args.pop()
        args_hashes = self.fileHashesInDir(item)

        for arg in args:
            try:
                self.assertDirEqual(arg, args_hashes)
            except AssertionError:
                raise AssertionError(
                    "The directory `{first}` and the directory `{second}` are not equal.Files in {first}:\n{first_files}\n\nFiles in {second}:\n{second_files}\n".
                    format(
                        first=self.joinPath(arg),
                        second=self.joinPath(item),
                        first_files=self.fileHashesInDir(arg),
                        second_files=args_hashes,
                    ))

    def assertFilesEqual(self, *rel_args):
        """
        Checks if two files have the same length and content.

        fil1 == fil2 and fil1 == fil3 and ... and fil1 == filN

        Arguments
        ---------
            rel_args: List of file paths (relative)
        """
        if len(rel_args) < 2:
            raise AssertionError("Need two files to compare.")

        args = list(rel_args)
        last_item = self.joinPath(args.pop())
        last_hash = client.shorthand.hash_file(last_item)

        for arg in args:
            arg = self.joinPath(arg)
            arg_hash = client.shorthand.hash_file(arg)

            if arg_hash != last_hash:
                raise ValueError(
                    "File `{}` and file `{}` are not equal!".format(
                        last_item,
                        arg,
                    ))

    def assertDirEqual(self, rel_path, file_hashes):
        """
        Checks if the given files are in the path.

        Arguments
        ---------
            rel_path: string (relative)
            file_hashes: array of hashes

        """
        path_hashes = self.fileHashesInDir(rel_path)

        if len(path_hashes) != len(file_hashes):
            raise AssertionError(
                "The two lists are not the same length. Left:\n{}\n\nRight:\n{}".
                format(
                    path_hashes,
                    file_hashes,
                ))

        if set(file_hashes) != set(path_hashes):
            raise ValueError(
                "The directory `{}` does not contain the files with the hashes:\n{}".
                format(
                    self.joinPath(rel_path),
                    '\n'.join(list(file_hashes)),
                ))

    def provideFile(self, rel_path, data=None):
        """
        Creates a file within the folder environment.

        Arguments
        ---------
            path: path to file (relative)
            data: is written to the file

        Returns
        -------
            (absolute path, file content, hash value)
        """
        path = self.joinPath(rel_path)

        if os.path.isfile(path):
            raise AssertionError(
                "Can not create file `{}` because a file with the same name allready exists. All files:\n{}".
                format(path, '\n'.join(self.filesInDir())))

        if os.path.isdir(path):
            raise AssertionError(
                "Can not create file `{}` because a directory with the same name allready exists. All directories:\n{}".
                format(path, '\n'.join(self.dirsInDir())))

        if data is None:
            data = random_string(0, 1000)

        with open(path, 'w') as nfile:
            nfile.write(data)

        hash_value = hashlib.md5()
        hash_value.update(str(data).encode('utf-8'))

        return (path, data, hash_value.hexdigest())

    def joinPath(self, path):
        """
        Joins a given path with the environment path.

        Arguments
        ---------
            path: a path (relative)

        Returns
        -------
            string path
        """
        path = os.path.normpath(path)
        path = os.path.normcase(path)

        if '..' in path:
            raise AssertionError(
                "The path for a new file does not allow relative paths, which would go outside of the directory environment. ({})".
                format(path))

        return os.path.join(self.working_dir, path)

    def provideDirectory(self, path):
        """
        Creates a directory within the folder environment.

        Arguments
        ---------
            path: path to file (relative)

        Returns
        -------
            absolute path
        """
        path = self.joinPath(path)

        if os.path.isfile(path):
            raise AssertionError(
                "Can not create directory `{}` because a file with the same name allready exists.".
                format(path))

        if os.path.isdir(path):
            raise AssertionError(
                "Can not create directory `{}` because a directory with the same name allready exists.".
                format(path))

        os.mkdir(path)

        return path

    def provideFilledDirectory(self, path, files=None):
        """
        Creates a directory in an environment and fills it with random files to provide a
        hash value.

        Arguments
        ---------
            path: path to the directory (relative)
            files: array of file names

        Returns
        -------
            (absolute path, files, hash value)
        """
        abs_path = self.provideDirectory(path)
        abs_files = []

        if files is None:
            files = []
            for _ in range(0, random.randint(0, 30)):
                pat = ""

                for _ in range(0, random.randint(0, 4)):
                    if random.randint(0, 1):
                        pat += random_string(5, 15)

                files.append((pat, random_string(5, 15)))

        for (pat, fil) in files:
            pat = os.path.join(path, pat)

            if pat != "":
                os.makedirs(self.joinPath(pat), exist_ok=True)

            abs_files.append(self.provideFile(os.path.join(pat, fil)))

        md5 = hashlib.md5()

        for abs_file in abs_files:
            md5.update(abs_file[1].encode('utf-8'))

        return (abs_path, abs_files, '{}'.format(md5.hexdigest()))
