import unittest
import asyncio
import os

from os import remove, getcwd
from os.path import join, isfile

from utils import Rpc
import client.command

from client.command import Helper


class EventLoopTestCase(unittest.TestCase):
    """
    A TestCase class which provides an event loop, to test async functions.
    """

    @classmethod
    def setUpClass(cls):
        super(EventLoopTestCase, cls).setUpClass()

        if os.name == 'nt':
            cls.loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(cls.loop)
        else:
            cls.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls.loop)

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()


class TestFile:
    """
    A class which will generate a file.

    Format:
        [
            (PATH, CREATE),
            ...
        ]
    """

    def __init__(self, base, paths):
        self.paths = paths
        self.file = None
        self.base = base

    def __enter__(self):
        for (path, create) in self.paths:
            if create:
                path = os.path.join(self.base, path)

                if os.path.exists(path):
                    raise ValueError(
                        "File allready exists ... can not override!")

                print("Creating file {}".format(path))
                open(path, "w").close()

        return list(map(lambda x: os.path.join(self.base, x[0]), self.paths))

    def __exit__(self, type, value, traceback):
        print(os.listdir(self.base))

        errors = []

        for (path, created) in self.paths:
            path = os.path.join(self.base, path)

            if not os.path.exists(path):
                if created:
                    errors.append(path)
            else:
                print("Deleting file {}".format(path))
                os.remove(path)

        if errors:
            raise ValueError("Could not delete crated file: {}".format(errors))


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


class FileCommandTests(EventLoopTestCase):
    @classmethod
    def setUpClass(cls):
        super(FileCommandTests, cls).setUpClass()

        cls.backup_ending = "_BACK"
        cls.working_dir = os.path.abspath('./unittest.filecommand/')

        if not os.path.exists(cls.working_dir):
            os.mkdir(cls.working_dir)

    @classmethod
    def tearDownClass(cls):
        super(FileCommandTests, cls).tearDownClass()
        os.rmdir(cls.working_dir)

    def setUp(self):
        self.assertTrue(len(os.listdir(self.working_dir)) == 0)

    def tearDown(self):
        self.assertTrue(len(os.listdir(self.working_dir)) == 0)

    def test_move_file_destination_exists(self):
        source = "test.abc"
        destination = "test.abc.link"
        backup = destination + self.backup_ending

        with TestFile(self.working_dir, [
            (source, True),
            (destination, True),
            (backup, False),
        ]) as (source, destination, backup):
            self.loop.run_until_complete(
                client.command.move_file(source, destination,
                                         self.backup_ending))

            self.assertTrue(os.path.isfile(destination))
            self.assertTrue(os.path.isfile(backup))

    def test_move_file_destination_not_exists(self):
        source = "test.abc"
        destination = "test.abc.link"
        backup = destination + self.backup_ending

        with TestFile(self.working_dir, [
            (source, True),
            (destination, False),
            (backup, False),
        ]) as (source, destination, backup):
            self.loop.run_until_complete(
                client.command.move_file(source, destination,
                                         self.backup_ending))

            self.assertTrue(os.path.isfile(destination))
            self.assertFalse(os.path.isfile(backup))

    def test_move_file_source_not_exists(self):
        source = "test.abc"
        destination = "test.abc.link"

        self.assertRaises(
            FileNotFoundError,
            self.loop.run_until_complete,
            client.command.move_file(
                source,
                destination,
                self.backup_ending,
            ),
        )

        self.assertFalse(os.path.isfile(destination))

    def test_move_file_backup_exists(self):
        source = "test.abc"
        destination = "test.abc.link"
        backup = destination + self.backup_ending

        with TestFile(self.working_dir, [
            (source, True),
            (destination, True),
            (backup, True),
        ]) as (source, destination, backup):
            self.assertRaises(FileExistsError, self.loop.run_until_complete,
                              client.command.move_file(
                                  source,
                                  destination,
                                  self.backup_ending,
                              ))

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
