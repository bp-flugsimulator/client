import unittest
import asyncio
import os
import random
import string
from hashlib import md5

from os import remove, getcwd
from os.path import join, isfile
from uuid import uuid4

from utils import Rpc
import client.command
from client.logger import LOGGER

from client.command import Helper


class EventLoopTestCase(unittest.TestCase):
    """
    A TestCase class which provides an event loop, to test async functions.
    """

    @classmethod
    def setUpClass(cls):
        super(EventLoopTestCase, cls).setUpClass()

        LOGGER.enable()

        if os.name == 'nt':
            cls.loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(cls.loop)
        else:
            cls.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls.loop)

    @classmethod
    def tearDownClass(cls):
        super(EventLoopTestCase, cls).tearDownClass()
        cls.loop.close()
        LOGGER.disable()

class TestFile:
    """
    A class which will generate a file.

    Format:
        [
            (PATH, CREATE),
            ...
        ]
    """

    def __init__(self, base, paths, removing=False):
        self.paths = paths
        self.base = base
        self.removing = removing

    def __enter__(self):
        for (path, create) in self.paths:
            if create:
                path = os.path.join(self.base, path)

                if os.path.exists(path):
                    raise ValueError(
                        "File allready exists ... can not override!")

                print("Creating file {}".format(path))

                with open(path, "w") as fil:
                    fil.write(str(create))

        return list(map(lambda x: os.path.join(self.base, x[0]), self.paths))

    def __exit__(self, type, value, traceback):
        print(os.listdir(self.base))

        errors = []

        for path, _ in self.paths:
            path = os.path.join(self.base, path)

            if not os.path.exists(path):
                if not self.removing:
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
            client.command.execute(uuid4().hex, "calcs.exe",
                                   "this is a arguments list"),
        )

    def test_execution_wrong_prog_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute(uuid4().hex, ["calcs.exe"], []),
        )

    def test_execution_wrong_arguments_elements(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute(uuid4().hex, "calcs.exe", [1, 2, 34]),
        )

    def test_execution_echo_shell(self):
        if os.name == 'nt':
            prog = "C:\\Windows\\System32\\cmd.exe"
            args = ["/c", "ECHO %date%"]
        else:
            prog = "/bin/sh"
            args = ["-c", "echo $(date)"]

        self.assertEqual(
            '0',
            self.loop.run_until_complete(
                client.command.execute(uuid4().hex, prog, args)),
        )

    def test_online(self):
        result = self.loop.run_until_complete(client.command.online())
        self.assertIsNone(result)

    def test_execution_directory(self):
        path = join(getcwd(), 'applications')
        if os.name == 'nt':
            prog = join(path, 'echo.bat')
        else:
            prog = join(path, 'echo.sh')

        self.assertEqual('0',
                         self.loop.run_until_complete(
                             client.command.execute(uuid4().hex,prog, [])))
        self.assertTrue(isfile(join(path, 'test.txt')))
        remove(join(path, 'test.txt'))

    def _test_cancel_execution(self):
        if os.name == 'nt':
            prog = "C:\\Windows\\System32\\cmd.exe"
            args = ["/c", "notepad.exe"]
            return_code = '15'
        else:
            prog = "/bin/bash"
            args = ['-c', '"sleep 100"']
            return_code = '143'  # TODO why not -15 ???

        @asyncio.coroutine
        def create_and_cancel_task():
            task = self.loop.create_task(
                client.command.execute(uuid4().hex, prog, args))
            yield from asyncio.sleep(0.5)
            task.cancel()
            print("canceled task")
            result = yield from task
            return result

        res = self.loop.run_until_complete(create_and_cancel_task())
        self.assertEqual(return_code, res)

    def test_get_log(self):
        uuid = uuid4().hex
        message = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
        self.assertEqual('0',
                         self.loop.run_until_complete(
                             client.command.execute(uuid, 'echo', [message])))

        res = self.loop.run_until_complete(client.command.get_log(uuid))
        if os.name == 'nt':
            self.assertIn(
                'echo  ' + message + ' \r\n ' + message + '\r\n',
                res['log'],
            )

        else:
            self.assertIn(
                message + '\n',
                res['log'],
            )

        self.assertEqual(
            uuid,
            res['uuid'],
        )

    def test_get_log_unknown_uuid(self):
        self.assertRaises(FileNotFoundError, self.loop.run_until_complete,
                          client.command.get_log('abcdefg'))


class FileCommandTests(EventLoopTestCase):
    @classmethod
    def setUpClass(cls):
        super(FileCommandTests, cls).setUpClass()

        cls.backup_ending = "_BACK"
        cls.working_dir = os.path.abspath('./unittest.filecommand/')

        allow_chars = string.ascii_letters + string.digits

        string1 = ''.join([random.choice(allow_chars) for n in range(32)])
        string2 = ''.join([random.choice(allow_chars) for n in range(32)])

        m1 = md5()
        m1.update(string1.encode('utf-8'))

        m2 = md5()
        m2.update(string2.encode('utf-8'))

        cls.hash1 = ("{}".format(m1.hexdigest()), string1)
        cls.hash2 = ("{}".format(m2.hexdigest()), string2)

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

    def test_move_file_source_directory(self):
        source = os.path.join(self.working_dir, "testdir_source")
        os.mkdir(source)

        try:
            self.assertRaises(
                ValueError,
                self.loop.run_until_complete,
                client.command.move_file(source, "", self.backup_ending),
            )
        finally:
            os.rmdir(source)

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

        with TestFile(self.working_dir, [
            (source, True),
            (destination, False),
        ]) as (source, destination):
            self.loop.run_until_complete(
                client.command.move_file(source, destination,
                                         self.backup_ending))

            self.assertTrue(os.path.isfile(destination))

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

    def test_move_file_destination_folder_success(self):
        source = "test.abc"
        destination = "./testdir"

        os.mkdir(os.path.join(self.working_dir, destination))

        try:
            with TestFile(self.working_dir, [
                (source, True),
                (os.path.join(destination, source), False),
            ]) as (source, destination_file):
                self.loop.run_until_complete(
                    client.command.move_file(
                        source,
                        os.path.join(self.working_dir, destination),
                        self.backup_ending,
                    ))

                self.assertTrue(os.path.exists(destination_file))
        finally:
            os.rmdir(os.path.join(self.working_dir, destination))

    def test_move_file_destination_folder_destination_exist(self):
        source = "test.abc"
        destination = "./testdir"
        backup = source + self.backup_ending

        os.mkdir(os.path.join(self.working_dir, destination))

        try:
            with TestFile(self.working_dir, [
                (source, True),
                (os.path.join(destination, source), True),
                (os.path.join(destination, backup), False),
            ]) as (source, destination_file, backup_file):
                self.loop.run_until_complete(
                    client.command.move_file(
                        source,
                        os.path.join(self.working_dir, destination),
                        self.backup_ending,
                    ))

                self.assertTrue(os.path.exists(destination_file))
                self.assertTrue(os.path.exists(backup_file))
        finally:
            os.rmdir(os.path.join(self.working_dir, destination))

    def test_move_file_destination_folder_backup_exist(self):
        source = "test.abc"
        destination = "./testdir"
        backup = source + self.backup_ending

        os.mkdir(os.path.join(self.working_dir, destination))

        try:
            with TestFile(self.working_dir, [
                (source, True),
                (os.path.join(destination, source), True),
                (os.path.join(destination, backup), True),
            ]) as (source, destination_file, backup_file):
                self.assertRaises(
                    FileExistsError, self.loop.run_until_complete,
                    client.command.move_file(
                        source,
                        os.path.join(self.working_dir, destination),
                        self.backup_ending,
                    ))

                self.assertTrue(os.path.exists(destination_file))
                self.assertTrue(os.path.exists(backup_file))
        finally:
            os.rmdir(os.path.join(self.working_dir, destination))

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
        source = "test.abc"
        destination = "test.abc.link"

        with TestFile(
                self.working_dir,
            [
                (source, self.hash1[1]),
                (destination, False),
            ],
                removing=True,
        ) as (source, destination):
            self.loop.run_until_complete(
                client.command.move_file(
                    source,
                    destination,
                    self.backup_ending,
                ))

            self.assertTrue(os.path.exists(destination))

            self.loop.run_until_complete(
                client.command.restore_file(
                    source,
                    destination,
                    self.backup_ending,
                    self.hash1[0],
                ))

            self.assertFalse(os.path.exists(destination))

    def test_restore_file_with_backup(self):
        source = "test.abc"
        destination = "test.abc.link"
        backup = destination + self.backup_ending

        with TestFile(
                self.working_dir,
            [
                (source, self.hash1[1]),
                (destination, False),
                (backup, self.hash2[1]),
            ],
                removing=True,
        ) as (source, destination, backup):
            self.loop.run_until_complete(
                client.command.move_file(
                    source,
                    destination,
                    self.backup_ending,
                ))

            self.assertTrue(os.path.exists(destination))

            self.loop.run_until_complete(
                client.command.restore_file(
                    source,
                    destination,
                    self.backup_ending,
                    self.hash1[0],
                ))

            self.assertFalse(os.path.exists(backup))
            self.assertTrue(os.path.exists(destination))

            with open(destination, 'r') as file:
                self.assertEqual(file.read(), self.hash2[1])

    def test_restore_file_no_destination_with_backup(self):
        source = "test.abc"
        destination = "test.abc.link"
        backup = destination + self.backup_ending

        with TestFile(
                self.working_dir,
            [
                (source, self.hash1[1]),
                (destination, False),
                (backup, self.hash2[1]),
            ],
                removing=True,
        ) as (source, destination, backup):
            self.assertFalse(os.path.exists(destination))

            self.loop.run_until_complete(
                client.command.restore_file(
                    source,
                    destination,
                    self.backup_ending,
                    self.hash1[0],
                ))

            self.assertFalse(os.path.exists(backup))
            self.assertTrue(os.path.exists(destination))
            with open(destination, 'r') as file:
                self.assertEqual(file.read(), self.hash2[1])

    def test_restore_file_no_destination(self):
        source = "test.abc"
        destination = "test.abc.link"

        with TestFile(
                self.working_dir,
            [
                (source, self.hash1[1]),
                (destination, False),
            ],
                removing=True,
        ) as (source, destination):
            self.assertFalse(os.path.exists(destination))

            self.loop.run_until_complete(
                client.command.restore_file(
                    source,
                    destination,
                    self.backup_ending,
                    self.hash1[0],
                ))

            self.assertFalse(os.path.exists(destination))

    def test_restore_file_replaced(self):
        source = "test.abc"
        destination = "test.abc.link"

        with TestFile(
                self.working_dir,
            [
                (source, self.hash1[1]),
                (destination, self.hash2[1]),
            ],
                removing=True,
        ) as (source, destination):
            self.assertTrue(os.path.exists(destination))

            self.assertRaises(
                ValueError,
                self.loop.run_until_complete,
                client.command.restore_file(
                    source,
                    destination,
                    self.backup_ending,
                    self.hash1[0],
                ),
            )

            self.assertTrue(os.path.exists(destination))

    def test_restore_file_modified(self):
        source = "test.abc"
        destination = "test.abc.link"

        with TestFile(
                self.working_dir,
            [
                (source, self.hash1[1]),
                (destination, self.hash1[1]),
            ],
                removing=True,
        ) as (source, destination):
            self.assertTrue(os.path.exists(destination))
            self.loop.run_until_complete(
                client.command.restore_file(
                    source,
                    destination,
                    self.backup_ending,
                    self.hash2[0],
                ))

            self.assertFalse(os.path.exists(destination))

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
