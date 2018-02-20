"""
Unit tests for the module client.command.
"""
#pylint: disable=C0111, C0103
import unittest
import asyncio
import os
import shutil

from os import remove, getcwd
from os.path import join, isfile
from utils import Rpc, Status

from .testcases import EventLoopTestCase, FileSystemTestCase
import client.command
from client.command import Helper


class TestCommands(EventLoopTestCase):
    def test_remove_trailing(self):
        path = "/home/user/test/"
        self.assertEqual("", os.path.basename(path))
        self.assertEqual(
            "test",
            os.path.basename(
                client.command.remove_trailing_path_seperator(path)))

    def test_remove_trailing_no_remove(self):
        path = "/home/user/test"
        self.assertEqual("test", os.path.basename(path))
        self.assertEqual(
            "test",
            os.path.basename(
                client.command.remove_trailing_path_seperator(path)))

    def test_remove_trailing_empty(self):
        path = ""
        self.assertEqual("", os.path.basename(path))
        self.assertEqual(
            "",
            os.path.basename(
                client.command.remove_trailing_path_seperator(path)))

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
                'uuid': 'thisisunique',
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
            'thisisunique',
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
            client.command.chain_execution(
                commands=[{
                    'method': 'execute',
                    'uuid': 'uniqueidforfirst',
                    'arguments': {
                        'path': prog,
                    },
                }, {
                    'method': 'execute',
                    'uuid': 'uniqueidforsecond',
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
            'uniqueidforfirst',
        )

        response2 = Status(
            Status.ID_ERR,
            {
                'method':
                'execute',
                'result':
                'Could not execute because earlier command was not successful.',
            },
            'uniqueidforsecond',
        )

        self.assertEqual(Status(**result[0]), response1)
        self.assertEqual(Status(**result[1]), response2)


class FileCommandFilesTests(FileSystemTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.backup_ending = "_BACK"

    def test_filesystem_move_destination_exists(self):
        (source, _, _) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile("test.abc.link")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
            ))

        self.assertFilesArePresent(destination, backup, source)

    def test_filesystem_move_destination_not_exists(self):
        (source, _, _) = self.provideFile("test.abc")
        destination = self.joinPath("test.abc.link")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(backup, destination)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
            ))

        self.assertFilesArePresent(destination, source)
        self.assertFilesAreNotPresent(backup)

    def test_filesystem_move_source_not_exists(self):
        source = self.joinPath("test.abc")
        (destination, _, _) = self.provideFile("test.abc.link")

        self.assertFilesArePresent(destination)
        self.assertFilesAreNotPresent(source)

        self.assertRaises(
            FileNotFoundError,
            self.loop.run_until_complete,
            client.command.filesystem_move(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
            ),
        )

        self.assertFilesArePresent(destination)
        self.assertFilesAreNotPresent(source)

    def test_filesystem_move_backup_exists(self):
        (source, _, _) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile("test.abc.link")
        (backup, _, _) = self.provideFile("test.abc.link" + self.backup_ending)

        self.assertFilesArePresent(source, destination, backup)

        self.assertRaises(
            FileExistsError,
            self.loop.run_until_complete,
            client.command.filesystem_move(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
            ),
        )

        self.assertFilesArePresent(source, destination, backup)

    def test_filesystem_move_destination_folder_success(self):
        (source, _, _) = self.provideFile("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        destination = self.joinPath("this_is_my_folder/test.abc")

        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(backup, destination)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "file",
                destination_path,
                "dir",
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)
        self.assertDirsArePresent(destination_path)

    def test_filesystem_move_destination_folder_destination_exist(self):
        (source, _, _) = self.provideFile("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (destination, _, _) = self.provideFile("this_is_my_folder/test.abc")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "file",
                destination_path,
                "dir",
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination, backup)
        self.assertDirsArePresent(destination_path)

    def test_filesystem_move_destination_folder_backup_exist(self):
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
            client.command.filesystem_move(
                source,
                "file",
                destination_path,
                "dir",
                self.backup_ending,
            ),
        )

        self.assertFilesArePresent(source, destination, backup)
        self.assertDirsArePresent(destination_path)

    def test_filesystem_restore_no_backup(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        destination = self.joinPath("test.abc.link")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination, backup)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination, backup)

    def test_filesystem_restore_no_backup_destination_dir(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (destination, _, _) = self.provideFile("this_is_my_folder/test.abc")
        backup = self.joinPath("this_is_my_folder/test.abc" +
                               self.backup_ending)

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "file",
                destination_path,
                "dir",
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination, backup)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "file",
                destination_path,
                "dir",
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)
        self.assertDirsArePresent(destination_path)

    def test_filesystem_restore_with_backup(self):
        (source, data_source, hash_source) = self.provideFile("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (
            destination,
            data_destination,
            _,
        ) = self.provideFile("this_is_my_folder/test.abc")
        backup = self.joinPath("this_is_my_folder/test.abc" +
                               self.backup_ending)

        self.assertFilesArePresent(source, destination)
        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "file",
                destination_path,
                "dir",
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination, backup)

        with open(destination, 'r') as clone:
            self.assertEqual(clone.read(), data_source)

        self.assertDirsArePresent(destination_path)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "file",
                destination_path,
                "dir",
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source, destination)

        with open(destination, 'r') as clone:
            self.assertEqual(clone.read(), data_destination)

        self.assertDirsArePresent(destination_path)

    def test_filesystem_restore_no_destination_with_backup(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        destination = self.joinPath("test.abc.link")

        (
            backup,
            data_backup,
            _,
        ) = self.provideFile("test.abc.link" + self.backup_ending)

        self.assertFilesArePresent(source, backup)
        self.assertFilesAreNotPresent(destination)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        with open(destination, 'r') as clone:
            self.assertEqual(clone.read(), data_backup)

    def test_filesystem_restore_no_destination(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        destination = self.joinPath("test.abc.link")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination, backup)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination, backup)

    def test_filesystem_restore_replaced(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        (destination, _, _) = self.provideFile("test.abc.link")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        self.assertRaisesRegex(
            ValueError,
            "file .* was changed while it was replaced",
            self.loop.run_until_complete,
            client.command.filesystem_restore(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ),
        )

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

    def test_filesystem_restore_modified(self):
        (source, _, hash_source) = self.provideFile("test.abc")
        destination = self.joinPath("test.abc.link")
        backup = destination + self.backup_ending

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(backup, destination)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
            ))

        self.assertFilesArePresent(source, destination)
        self.assertFilesAreNotPresent(backup)

        with open(destination, 'w+') as clone:
            clone.write("test")

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ))

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(backup, destination)


class FileCommandDirsTests(FileSystemTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.backup_ending = "_BACK"

    def test_filesystem_move_destination_exists(self):
        (source, _, _) = self.provideFilledDirectory("test.abc")
        (destination, _, _) = self.provideFilledDirectory("test.abc.link")
        backup = destination + self.backup_ending

        self.assertDirsArePresent(source, destination)
        self.assertDirsAreNotPresent(backup)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
            ))

        self.assertDirsArePresent(destination, backup, source)

    def test_filesystem_move_destination_not_exists(self):
        (source, _, _) = self.provideFilledDirectory("test.abc")
        destination = self.joinPath("test.abc.link")
        backup = destination + self.backup_ending

        self.assertDirsArePresent(source)
        self.assertDirsAreNotPresent(backup, destination)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
            ))

        self.assertDirsArePresent(destination, source)
        self.assertDirsAreNotPresent(backup)

    def test_filesystem_move_source_not_exists(self):
        source = self.joinPath("test.abc")
        (destination, _, _) = self.provideFilledDirectory("test.abc.link")

        self.assertDirsArePresent(destination)
        self.assertDirsAreNotPresent(source)

        self.assertRaises(
            FileNotFoundError,
            self.loop.run_until_complete,
            client.command.filesystem_move(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
            ),
        )

        self.assertDirsArePresent(destination)
        self.assertDirsAreNotPresent(source)

    def test_filesystem_move_backup_exists(self):
        (source, _, _) = self.provideFilledDirectory("test.abc")
        (destination, _, _) = self.provideFilledDirectory("test.abc.link")
        (backup, _,
         _) = self.provideFilledDirectory("test.abc.link" + self.backup_ending)

        self.assertDirsArePresent(source, destination, backup)

        self.assertRaises(
            FileExistsError,
            self.loop.run_until_complete,
            client.command.filesystem_move(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
            ),
        )

        self.assertDirsArePresent(source, destination, backup)

    def test_filesystem_move_destination_folder_success(self):
        (source, _, _) = self.provideFilledDirectory("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        destination = self.joinPath("this_is_my_folder/test.abc")
        backup = destination + self.backup_ending

        self.assertDirsAreNotPresent(backup, destination)
        self.assertDirsArePresent(destination_path, source)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "dir",
                destination_path,
                "dir",
                self.backup_ending,
            ))

        self.assertDirsAreNotPresent(backup)
        self.assertDirsArePresent(destination_path, source, destination)

    def test_filesystem_move_destination_folder_destination_exist(self):
        (source, _, _) = self.provideFilledDirectory("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (destination, _,
         _) = self.provideFilledDirectory("this_is_my_folder/test.abc")
        backup = destination + self.backup_ending

        self.assertDirsAreNotPresent(backup)
        self.assertDirsArePresent(destination_path, source, destination)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "dir",
                destination_path,
                "dir",
                self.backup_ending,
            ))

        self.assertDirsArePresent(source, destination, backup,
                                  destination_path)

    def test_filesystem_move_destination_folder_backup_exist(self):
        (source, _, _) = self.provideFilledDirectory("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (destination, _,
         _) = self.provideFilledDirectory("this_is_my_folder/test.abc")
        (backup, _, _) = self.provideFilledDirectory(
            "this_is_my_folder/test.abc" + self.backup_ending)

        self.assertDirsArePresent(source, destination, backup,
                                  destination_path)

        self.assertRaises(
            FileExistsError,
            self.loop.run_until_complete,
            client.command.filesystem_move(
                source,
                "dir",
                destination_path,
                "dir",
                self.backup_ending,
            ),
        )

        self.assertDirsArePresent(source, destination, backup,
                                  destination_path)

    def test_filesystem_restore_no_backup(self):
        (source, _, hash_source) = self.provideFilledDirectory("test.abc")
        destination = self.joinPath("test.abc.link")
        backup = destination + self.backup_ending

        self.assertDirsArePresent(source)
        self.assertDirsAreNotPresent(destination, backup)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
            ))

        self.assertDirsArePresent(source, destination)
        self.assertDirsAreNotPresent(backup)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ))

        self.assertDirsArePresent(source)
        self.assertDirsAreNotPresent(destination, backup)

    def test_filesystem_restore_no_backup_destination_dir(self):
        (source, _, hash_source) = self.provideFilledDirectory("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (destination, _,
         _) = self.provideFilledDirectory("this_is_my_folder/test.abc")
        backup = self.joinPath("this_is_my_folder/test.abc" +
                               self.backup_ending)

        self.assertDirsArePresent(source, destination, destination_path)
        self.assertDirsAreNotPresent(backup)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "dir",
                destination_path,
                "dir",
                self.backup_ending,
            ))

        self.assertDirsArePresent(source, destination, backup,
                                  destination_path)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "dir",
                destination_path,
                "dir",
                self.backup_ending,
                hash_source,
            ))

        self.assertDirsArePresent(source, destination, destination_path)
        self.assertDirsAreNotPresent(backup)

    def test_filesystem_restore_with_backup(self):
        (source, _, hash_source) = self.provideFilledDirectory("test.abc")
        destination_path = self.provideDirectory("this_is_my_folder")
        (
            destination,
            files_destination,
            _,
        ) = self.provideFilledDirectory("this_is_my_folder/test.abc")

        backup = self.joinPath("this_is_my_folder/test.abc" +
                               self.backup_ending)

        self.assertDirsArePresent(source, destination, destination_path)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "dir",
                destination_path,
                "dir",
                self.backup_ending,
            ))

        self.assertDirsArePresent(source, destination, backup)
        self.assertDirsArePresent(destination_path)

        self.assertDirsEqual(destination, source)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "dir",
                destination_path,
                "dir",
                self.backup_ending,
                hash_source,
            ))

        self.assertDirsArePresent(source, destination, destination_path)
        self.assertDirEqual(destination,
                            list(map(
                                lambda f: f[2],
                                files_destination,
                            )))

    def test_filesystem_restore_no_destination_with_backup(self):
        (source, _, hash_source) = self.provideFilledDirectory("test.abc")
        destination = self.joinPath("test.abc.link")
        (
            backup,
            files_backup,
            _,
        ) = self.provideFilledDirectory("test.abc.link" + self.backup_ending)

        self.assertDirsArePresent(source, backup)
        self.assertDirsAreNotPresent(destination)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ))

        self.assertDirsArePresent(source, destination)
        self.assertDirsAreNotPresent(backup)

        self.assertDirEqual(destination,
                            list(map(lambda f: f[2], files_backup)))

    def test_filesystem_restore_no_destination(self):
        (source, _, hash_source) = self.provideFilledDirectory("test.abc")
        destination = self.joinPath("test.abc.link")
        backup = destination + self.backup_ending

        self.assertDirsArePresent(source)
        self.assertDirsAreNotPresent(destination, backup)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ))

        self.assertDirsArePresent(source)
        self.assertDirsAreNotPresent(destination, backup)

    def test_filesystem_restore_replaced(self):
        (source, _, hash_source) = self.provideFilledDirectory("test.abc")
        (destination, _, _) = self.provideFilledDirectory("test.abc.link")
        backup = destination + self.backup_ending

        self.assertDirsArePresent(source, destination)
        self.assertDirsAreNotPresent(backup)

        self.assertRaisesRegex(
            ValueError,
            "directory .* was changed while it was replaced",
            self.loop.run_until_complete,
            client.command.filesystem_restore(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ),
        )

        self.assertDirsArePresent(source, destination)
        self.assertDirsAreNotPresent(backup)

    def test_filesystem_restore_modified(self):
        (source, _, hash_source) = self.provideFilledDirectory("test.abc")
        destination = self.joinPath("test.abc.link")
        backup = destination + self.backup_ending

        self.assertDirsArePresent(source)
        self.assertDirsAreNotPresent(backup, destination)

        self.loop.run_until_complete(
            client.command.filesystem_move(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
            ))

        self.assertDirsArePresent(source, destination)
        self.assertDirsAreNotPresent(backup)

        # create a new file in source and destination
        new_file_name = "12345678901234567890123456"
        (new_file, _, _) = self.provideFile(
            os.path.join(destination, new_file_name))

        shutil.copy2(new_file,
                     self.joinPath(os.path.join(source, new_file_name)))

        self.assertDirsEqual(source, destination)

        self.loop.run_until_complete(
            client.command.filesystem_restore(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
                hash_source,
            ))

        self.assertDirsArePresent(source)
        self.assertDirsAreNotPresent(backup, destination)


class FileCommandTypesTests(FileSystemTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.backup_ending = "_BACK"

    def test_hash_file_not_found(self):
        self.provideDirectory("test")
        self.assertRaisesRegex(
            ValueError,
            "The given path .* is not a file",
            client.command.hash_file,
            self.joinPath("test"),
        )

    def test_hash_dir_not_found(self):
        self.provideFile("test")
        self.assertRaisesRegex(
            ValueError,
            "The given path .* is not a directory",
            client.command.hash_directory,
            self.joinPath("test"),
        )

    def test_filesystem_move_source_not_exists_wrong_type_dir(self):
        (source, _, _) = self.provideFile("test.abc")
        destination = self.joinPath("test.abc.link")

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination)

        self.assertRaisesRegex(
            ValueError,
            "source path .* is not a directory",
            self.loop.run_until_complete,
            client.command.filesystem_move(
                source,
                "dir",
                destination,
                "file",
                self.backup_ending,
            ),
        )

        self.assertFilesArePresent(source)
        self.assertFilesAreNotPresent(destination)

    def test_filesystem_move_source_not_exists_wrong_type_file(self):
        source = self.provideDirectory("test.abc")
        destination = self.joinPath("test.abc.link")

        self.assertDirsArePresent(source)
        self.assertFilesAreNotPresent(destination)

        self.assertRaisesRegex(
            ValueError,
            "source path .* is not a file",
            self.loop.run_until_complete,
            client.command.filesystem_move(
                source,
                "file",
                destination,
                "file",
                self.backup_ending,
            ),
        )

        self.assertDirsArePresent(source)
        self.assertFilesAreNotPresent(destination)

    def test_filesystem_wrong_source_type_object(self):
        self.assertRaisesRegex(
            ValueError,
            "source_type",
            self.loop.run_until_complete,
            client.command.filesystem_restore("file.txt", "none", "ende",
                                              "file", "string", "hash"),
        )

    def test_filesystem_wrong_destination_type_object(self):
        self.assertRaisesRegex(
            ValueError,
            "destination_type",
            self.loop.run_until_complete,
            client.command.filesystem_restore("file.txt", "file", "ende",
                                              "none", "string", "hash"),
        )
