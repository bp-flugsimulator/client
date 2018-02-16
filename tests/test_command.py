import unittest
import asyncio
import os
import random
import string
import shutil

from hashlib import md5

from os import remove, getcwd
from os.path import join, isfile

from utils import Rpc, Status
import client.command

from client.command import Helper


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

    def assertFilesArePresent(self, *args):
        """
        Asserts that all listed files are in the directory. Use relative paths.

        Exception
        ---------
            AssertionError if a file is not in the directory.
        """
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
        """
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
        """
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

    def provideFile(self, path, data=None, exists=False, create=True):
        """
        Creates a file within the folder environment.

        Returns
        -------
            (absolute path, file content, hash)
        """
        path = os.path.normpath(path)
        path = os.path.normcase(path)

        if '..' in path:
            raise AssertionError(
                "The path for a new file does not allow relative paths, which would go outside of the directory environment. ({})".
                format(path))

        path = os.path.join(self.working_dir, path)

        if not exists and os.path.isfile(path):
            raise AssertionError(
                "Can not create file `{}` because a file with the same name allready exists.".
                format(path))

        if not exists and os.path.isdir(path):
            raise AssertionError(
                "Can not create file `{}` because a directory with the same name allready exists.".
                format(path))

        if data is None:
            length = random.randint(0, 1000)

            data = ''.join(
                random.choice(string.ascii_uppercase + string.digits)
                for _ in range(length))

        if create:
            with open(path, 'w') as nfile:
                nfile.write(data)

        hash_value = md5()
        hash_value.update(str(data).encode('utf-8'))

        return (path, data, hash_value.hexdigest())

    def provideDirectory(self, path, exists=False):
        """
        Creates a directory within the folder environment.

        Returns
        -------
            absolute path
        """
        path = os.path.normpath(path)
        path = os.path.normcase(path)

        if '..' in path:
            raise AssertionError(
                "The path for a new directory does not allow relative paths, which would go outside of the directory environment. ({})".
                format(path))

        path = os.path.join(self.working_dir, path)

        if not exists and os.path.isfile(path):
            raise AssertionError(
                "Can not create directory `{}` because a file with the same name allready exists.".
                format(path))

        if not exists and os.path.isdir(path):
            raise AssertionError(
                "Can not create directory `{}` because a directory with the same name allready exists.".
                format(path))

        os.mkdir(path)

        return path


class TestCommands(EventLoopTestCase):
    def test_all_functions_in_rpc(self):
        """
        Tests if all functions in commands are set with Rpc flag.
        """
        import types

        for func in dir(client.command):
            if Helper.get(func) is not None:
                continue

            if isinstance(getattr(client.command, func), types.FunctionType):
                self.assertEqual(getattr(client.command, func), Rpc.get(func))

    def test_execution_wrong_path_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute("calcs.exe", "this is a arguments list"),
        )

    def test_execution_wrong_prog_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute(["calcs.exe"], []),
        )

    def test_execution_wrong_arguments_elements(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute("calcs.exe", [1, 2, 34]),
        )

    def test_execution_not_existing_prog(self):
        self.assertRaises(
            FileNotFoundError,
            self.loop.run_until_complete,
            client.command.execute("calcs.exe", []),
        )

    def test_execution_echo_shell(self):
        if os.name == 'nt':
            prog = "C:\\Windows\\System32\\cmd.exe"
            args = ["/c", "ECHO %date%"]
        else:
            prog = "/bin/sh"
            args = ["-c", "echo $(date)"]

        self.assertEqual(
            0,
            self.loop.run_until_complete(client.command.execute(prog, args)),
        )

    def test_online(self):
        result = self.loop.run_until_complete(client.command.online())
        self.assertIsNone(result)

    def test_cancel_execution(self):
        if os.name == 'nt':
            prog = "C:\\Windows\\System32\\cmd.exe"
            args = ["/c", "notepad.exe"]
        else:
            prog = "/bin/sh"
            args = ["-c", "sleep 10"]

        @asyncio.coroutine
        def create_and_cancel_task():
            task = self.loop.create_task(client.command.execute(prog, args))
            yield from asyncio.sleep(0.1)
            task.cancel()
            result = yield from task
            return result

        res = self.loop.run_until_complete(create_and_cancel_task())
        self.assertTrue('Process got canceled and returned' in res)

    def test_execution_directory(self):
        path = join(getcwd(), 'applications')
        if os.name == 'nt':
            prog = join(path, 'echo.bat')
        else:
            prog = join(path, 'echo.sh')

        self.assertEqual(0,
                         self.loop.run_until_complete(
                             client.command.execute(prog, [])))
        self.assertTrue(isfile(join(path, 'test.txt')))
        remove(join(path, 'test.txt'))

    def test_chain_command_none(self):
        result = self.loop.run_until_complete(
            client.command.chain_execution(commands=[{
                'method': None,
                'uuid': None,
                'arguments': [],
            }]))

        self.assertEqual(result, [])

    def test_chain_command_success(self):
        if os.name == 'nt':
            prog = "C:\\Windows\\System32\\cmd.exe"
            args = ["/c", "ECHO %date%"]
        else:
            prog = "/bin/sh"
            args = ["-c", "echo $(date)"]

        result = self.loop.run_until_complete(
            client.command.chain_execution(commands=[{
                'method': 'execute',
                'uuid': 0,
                'arguments': {
                    'path': prog,
                    'arguments': args
                },
            }]))

        response = Status(
            Status.ID_OK,
            {
                'method': 'execute',
                'result': 0,
            },
            0,
        )

        self.assertEqual(Status(**result[0]), response)

    def test_chain_command_one_failed(self):
        if os.name == 'nt':
            prog = "C:\\Windows\\System32\\cmd.exe"
            args = ["/c", "ECHO %date%"]
        else:
            prog = "/bin/sh"
            args = ["-c", "echo $(date)"]

        result = self.loop.run_until_complete(
            client.command.chain_execution(commands=[{
                'method': 'execute',
                'uuid': 0,
                'arguments': {
                    'path': prog,
                },
            }, {
                'method': 'execute',
                'uuid': 0,
                'arguments': {
                    'path': prog,
                    'arguments': args
                },
            }]))

        response1 = Status(
            Status.ID_ERR,
            {
                'method':
                'execute',
                'result':
                "execute() missing 1 required positional argument: 'arguments'",
            },
            0,
        )

        response2 = Status(
            Status.ID_ERR,
            {
                'method':
                'execute',
                'result':
                'Could not execute because earlier command was not successful.',
            },
            0,
        )

        self.assertEqual(Status(**result[0]), response1)
        self.assertEqual(Status(**result[1]), response2)


class FileCommandTests(FileSystemTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.backup_ending = "_BACK"

    def test_move_file_source_directory(self):
        source = os.path.join(self.working_dir, "testdir_source")
        os.mkdir(source)

        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.move_file(source, "", self.backup_ending),
        )

    def test_move_file_destination_exists(self):
        (source, _, _) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile("test.abc.link")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        self.loop.run_until_complete(
            client.command.move_file(
                source,
                destination,
                self.backup_ending,
            ))

        self.assertFilesArePresent(destination, backup, source)

    def test_move_file_destination_not_exists(self):
        (source, _, _) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile("test.abc.link", create=False)
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(backup, destination)

        self.loop.run_until_complete(
            client.command.move_file(
                source,
                destination,
                self.backup_ending,
            ))

        self.assertFilesArePresent(destination, source)
        self.assertFilesAreNotPresent(backup)

    def test_move_file_source_not_exists(self):
        (source, _, _) = self.provideFile("test.abc", create=False)
        (destination, _, _) = self.provideFile("test.abc.link")

        self.assertFilesArePresent(destination)
        self.assertFilesAreNotPresent(source)

        self.assertRaises(
            FileNotFoundError,
            self.loop.run_until_complete,
            client.command.move_file(
                source,
                destination,
                self.backup_ending,
            ),
        )

        self.assertFilesArePresent(destination)
        self.assertFilesAreNotPresent(source)

    def test_move_file_backup_exists(self):
        (source, _, _) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile("test.abc.link")
        (backup, _, _) = self.provideFile("test.abc.link" + self.backup_ending)

        self.assertFilesArePresent(source, destination, backup)

        self.assertRaises(
            FileExistsError,
            self.loop.run_until_complete,
            client.command.move_file(
                source,
                destination,
                self.backup_ending,
            ),
        )

        self.assertFilesArePresent(source, destination, backup)

    def test_move_file_destination_folder_success(self):
        (source, _, _) = self.provideFile("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (destination, _, _) = self.provideFile(
            "this_is_my_folder/test.abc",
            create=False,
        )

        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(backup, destination)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.move_file(
                source,
                destination_path,
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)
        self.assertDirsArePresent(destination_path)

    def test_move_file_destination_folder_destination_exist(self):
        (source, _, _) = self.provideFile("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (destination, _, _) = self.provideFile("this_is_my_folder/test.abc")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.move_file(
                source,
                destination_path,
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination, backup)
        self.assertDirsArePresent(destination_path)

    def test_move_file_destination_folder_backup_exist(self):
        (source, _, _) = self.provideFile("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (destination, _, _) = self.provideFile("this_is_my_folder/test.abc")
        (backup, _, _) = self.provideFile("this_is_my_folder/test.abc" +
                                          self.backup_ending)

        self.assertFilesArePresent(source, destination, backup)
        self.assertDirsArePresent(destination_path)

        self.assertRaises(
            FileExistsError,
            self.loop.run_until_complete,
            client.command.move_file(
                source,
                destination_path,
                self.backup_ending,
            ),
        )

        self.assertFilesArePresent(source, destination, backup)
        self.assertDirsArePresent(destination_path)

    def test_move_file_wrong_source_path_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.move_file(1, "file.txt", "ende"),
        )

    def test_move_file_wrong_destination_path_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.move_file("file.txt", 1, "ende"),
        )

    def test_move_file_wrong_ending_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.move_file("file.txt", "ende", 1),
        )

    def test_restore_file_no_backup(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile(
            "test.abc.link",
            create=False,
        )
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination, backup)

        self.loop.run_until_complete(
            client.command.move_file(
                source,
                destination,
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        self.loop.run_until_complete(
            client.command.restore_file(
                source,
                destination,
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination, backup)

    def test_restore_file_no_backup_destination_dir(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (destination, _, _) = self.provideFile("this_is_my_folder/test.abc")
        (backup, _, _) = self.provideFile(
            "this_is_my_folder/test.abc" + self.backup_ending,
            create=False,
        )

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.move_file(
                source,
                destination_path,
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination, backup)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.restore_file(
                source,
                destination_path,
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)
        self.assertDirsArePresent(destination_path)

    def test_restore_file_with_backup(self):
        (source, data_source, hash_source) = self.provideFile("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (
            destination,
            data_destination,
            hash_destination,
        ) = self.provideFile("this_is_my_folder/test.abc")
        (backup, _, _) = self.provideFile(
            "this_is_my_folder/test.abc" + self.backup_ending,
            create=False,
        )

        self.assertFilesArePresent(source, destination)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.move_file(
                source,
                destination_path,
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination, backup)

        with open(destination, 'r') as clone:
            self.assertEqual(clone.read(), data_source)

        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.restore_file(
                source,
                destination_path,
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source, destination)

        with open(destination, 'r') as clone:
            self.assertEqual(clone.read(), data_destination)

        self.assertDirsArePresent(destination_path)

    def test_restore_file_no_destination_with_backup(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile(
            "test.abc.link",
            create=False,
        )
        (
            backup,
            data_backup,
            _,
        ) = self.provideFile("test.abc.link" + self.backup_ending)

        self.assertFilesArePresent(source, backup)
        self.assertFilesAreNotPresent(destination)

        self.loop.run_until_complete(
            client.command.restore_file(
                source,
                destination,
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        with open(destination, 'r') as clone:
            self.assertEqual(clone.read(), data_backup)

    def test_restore_file_no_destination(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile(
            "test.abc.link",
            create=False,
        )
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination, backup)

        self.loop.run_until_complete(
            client.command.restore_file(
                source,
                destination,
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination, backup)

    def test_restore_file_replaced(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile("test.abc.link")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.restore_file(
                source,
                destination,
                self.backup_ending,
                hash_source,
            ),
        )

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

    def test_restore_file_modified(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile("test.abc.link", create=False)
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(backup, destination)

        self.loop.run_until_complete(
            client.command.move_file(
                source,
                destination,
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        with open(destination, 'w+') as clone:
            clone.write("test")

        self.loop.run_until_complete(
            client.command.restore_file(
                source,
                destination,
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(backup, destination)

    def test_restore_file_source_dir(self):
        source_path = self.provideDirectory("test")
        (destination, _, hash_destination) = self.provideFile(
            "test.abc.link",
            create=False,
        )

        self.assertFilesAreNotPresent(destination, source_path)

        self.assertRaisesRegex(
            ValueError,
            "Moving a directory is not supported.",
            self.loop.run_until_complete,
            client.command.restore_file(
                source_path,
                destination,
                self.backup_ending,
                hash_destination,
            ),
        )

        self.assertFilesAreNotPresent(destination, source_path)

    def test_restore_file_wrong_source_path_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.restore_file(1, "file.txt", "ende", "hash"),
        )

    def test_restore_file_wrong_destination_path_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.restore_file("file.txt", 1, "ende", "hash"),
        )

    def test_restore_file_wrong_ending_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.restore_file("file.txt", "ende", 1, "hash"),
        )

    def test_restore_file_wrong_hash_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.restore_file("file.txt", "ende", "ende", 1),
        )
