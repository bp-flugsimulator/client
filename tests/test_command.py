"""
Unit tests for the module client.command.
"""
#pylint: disable=C0111, C0103
import unittest
import asyncio
import os
import sys
import random
import string
import websockets
import shutil

from os import remove, getcwd
from os.path import join, isfile
from uuid import uuid4

from utils import Rpc, Status

from .testcases import EventLoopTestCase, FileSystemTestCase
import client.command
import client.shorthand
from client.logger import LOGGER


class TestCommands(EventLoopTestCase):
    def test_execution_nonexisting_directory(self):
        path = os.path.join(os.getcwd(), 'appplications', 'tee.py')
        if os.name == 'nt':
            return_value = '1'
        else:
            return_value = '127'

        self.assertEqual(
            return_value,
            self.loop.run_until_complete(
                client.command.execute(
                    random.choice(string.digits),
                    uuid4().hex, path, [])),
        )

    def test_execution_wrong_path_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute(
                random.choice(string.digits),
                uuid4().hex, "calcs.exe", "this is a arguments list"),
        )

    def test_execution_wrong_prog_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute(
                random.choice(string.digits),
                uuid4().hex, ["calcs.exe"], []),
        )

    def test_execution_wrong_arguments_elements(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute(
                random.choice(string.digits),
                uuid4().hex, "calcs.exe", [1, 2, 34]),
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
                client.command.execute(
                    random.choice(string.digits),
                    uuid4().hex, prog, args)),
        )

    def test_online(self):
        result = self.loop.run_until_complete(client.command.online())
        self.assertIsNone(result)

    def test_execution_directory(self):
        path = join(getcwd(), 'applications')
        if os.name == 'nt':
            prog = join(path, 'folder with spaces', 'echo with spaces.bat')
        else:
            prog = join(path, 'folder with spaces', 'echo with spaces.sh')

        self.assertEqual('0',
                         self.loop.run_until_complete(
                             client.command.execute(
                                 random.choice(string.digits),
                                 uuid4().hex, prog, [])))
        self.assertTrue(isfile(join(path, 'folder with spaces', 'test.txt')))
        remove(join(path, 'folder with spaces', 'test.txt'))

    def test_cancel_execution_with_terminate(self):
        if os.name is 'nt':
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
                client.command.execute(
                    random.choice(string.digits),
                    uuid4().hex, prog, args))
            yield from asyncio.sleep(0.5)
            task.cancel()
            print("canceled task")
            result = yield from task
            return result

        res = self.loop.run_until_complete(create_and_cancel_task())
        self.assertEqual(return_code, res)

    def test_cancel_execution_with_kill(self):
        prog = sys.executable
        args = [join(getcwd(), 'applications', 'kill_me.py')]

        if os.name is 'nt':
            return_code = '15'
        else:
            return_code = '137'  # TODO why not -9 ???

        @asyncio.coroutine
        def create_and_cancel_task():
            task = self.loop.create_task(
                client.command.execute(
                    random.choice(string.digits),
                    uuid4().hex, prog, args))
            yield from asyncio.sleep(0.5)
            task.cancel()
            print("canceled task")
            result = yield from task
            return result

        res = self.loop.run_until_complete(create_and_cancel_task())
        self.assertEqual(return_code, res)

    def test_get_log(self):
        uuid = uuid4().hex
        message = ''.join([
            random.choice(string.ascii_letters + string.digits)
            for n in range(32)
        ])
        self.assertEqual('0',
                         self.loop.run_until_complete(
                             client.command.execute(
                                 random.choice(string.digits), uuid, 'echo',
                                 [message])))

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
        self.assertRaises(KeyError, self.loop.run_until_complete,
                          client.command.get_log('abcdefg'))

    def test_websocket_logging(self):
        if os.name is 'nt':
            prog = 'cmd'

            def sleep_hack(seconds):
                return 'ping 8.8.8.8 -n ' + seconds + ' >nul'

            args = [
                '/c',
                sleep_hack('3') + '& echo 0&' + sleep_hack('1') + ' & echo 1'
            ]
            expected_log = b'0\r\n1\r\n'
        else:
            prog = '/bin/bash'
            args = ['-c', '"sleep 3; echo 0; sleep 1; echo 1"']
            expected_log = b'0\n1\n'
        uuid = uuid4().hex

        @asyncio.coroutine
        def enable_logging():
            yield from asyncio.sleep(1)
            yield from client.command.enable_logging(uuid)

        @asyncio.coroutine
        def start_execution():
            yield from client.command.execute(
                random.choice(string.digits), uuid, prog, args)

        @asyncio.coroutine
        def start_server():
            finished = asyncio.Future()

            @asyncio.coroutine
            def websocket_handler(websocket, path):
                self.assertEqual('/logs', path)
                # receive log from file
                json = yield from websocket.recv()
                log = Status.from_json(json).payload['log'].encode()
                # ack
                yield from websocket.send('')

                #receive dynamic log
                while True:
                    json = yield from websocket.recv()
                    # ack
                    msg = Status.from_json(json).payload['log'].encode()
                    log += msg
                    if msg == b'':
                        break
                    else:
                        yield from websocket.send('')
                self.assertIn(expected_log, log)
                print('finished server')
                finished.set_result(None)

            server_handle = yield from websockets.serve(
                websocket_handler, host='127.0.0.1', port=8750)
            yield from finished
            server_handle.close()
            yield from server_handle.wait_closed()

        @asyncio.coroutine
        def wait_for_all():
            tasks = {
                start_server(),
                start_execution(),
                enable_logging(),
            }
            yield from asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            yield from client.command.disable_logging(uuid)

        LOGGER.url = 'ws://localhost:8750/logs'

        self.loop.run_until_complete(wait_for_all())

    def test_websocket_logging_early_disable(self):
        if os.name is 'nt':
            prog = 'cmd'

            def sleep_hack(seconds):
                return 'ping 8.8.8.8 -n ' + seconds + ' >nul'

            args = [
                '/c',
                sleep_hack('3') + '& echo 0&' + sleep_hack('3') + ' & echo 1'
            ]
            expected_log = b'0\r\n'
        else:
            prog = '/bin/bash'
            args = ['-c', '"sleep 3; echo 0; sleep 3; echo 1"']
            expected_log = b'0\n'
        uuid = uuid4().hex

        @asyncio.coroutine
        def enable_logging():
            yield from asyncio.sleep(1)
            yield from client.command.enable_logging(uuid)

        @asyncio.coroutine
        def disable_logging():
            yield from asyncio.sleep(4)
            yield from client.command.disable_logging(uuid)

        @asyncio.coroutine
        def start_execution():
            yield from client.command.execute(
                random.choice(string.digits), uuid, prog, args)

        @asyncio.coroutine
        def start_server():
            finished = asyncio.Future()

            @asyncio.coroutine
            def websocket_handler(websocket, path):
                self.assertEqual('/logs', path)
                # receive log from file
                json = yield from websocket.recv()
                log = Status.from_json(json).payload['log'].encode()
                # ack
                yield from websocket.send('')

                #receive dynamic log
                while True:
                    try:
                        json = yield from websocket.recv()
                        # ack
                        yield from websocket.send('')
                        msg = Status.from_json(json).payload['log'].encode()
                        if msg == b'':
                            break
                        log += msg
                    except websockets.exceptions.ConnectionClosed:
                        break
                self.assertIn(expected_log, log)
                print('finished server')
                finished.set_result(None)

            server_handle = yield from websockets.serve(
                websocket_handler, host='127.0.0.1', port=8750)
            yield from finished
            server_handle.close()
            yield from server_handle.wait_closed()

        @asyncio.coroutine
        def wait_for_all():
            tasks = {
                start_server(),
                start_execution(),
                enable_logging(),
                disable_logging(),
            }
            yield from asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

        LOGGER.url = 'ws://localhost:8750/logs'

        self.loop.run_until_complete(wait_for_all())

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
                    'pid': random.choice(string.digits),
                    'own_uuid': uuid4().hex,
                    'path': prog,
                    'arguments': args
                },
            }]))

        response = Status(
            Status.ID_OK,
            {
                'method': 'execute',
                'result': '0',
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
            client.command.chain_execution(commands=[{
                'method': 'execute',
                'uuid': 0,
                'arguments': {
                    'pid': 1,
                    'own_uuid': 0,
                    'path': prog,
                },
            }, {
                'method': 'execute',
                'uuid': 1,
                'arguments': {
                    'pid': 1,
                    'own_uuid': 1,
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
        (backup, _, _) = self.provideFile(
            "this_is_my_folder/test.abc" + self.backup_ending)

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
        backup = self.joinPath(
            "this_is_my_folder/test.abc" + self.backup_ending)

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
        backup = self.joinPath(
            "this_is_my_folder/test.abc" + self.backup_ending)

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

    """
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
    """

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
        backup = self.joinPath(
            "this_is_my_folder/test.abc" + self.backup_ending)

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

        backup = self.joinPath(
            "this_is_my_folder/test.abc" + self.backup_ending)

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

        self.assertDirEqual(destination, list(
            map(lambda f: f[2], files_backup)))

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
    """
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
    """

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


class FileCommandGenericTests(FileSystemTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.backup_ending = "_BACK"

    def test_hash_file_not_found(self):
        self.provideDirectory("test")
        self.assertRaisesRegex(
            ValueError,
            "The given path .* is not a file",
            client.shorthand.hash_file,
            self.joinPath("test"),
        )

    def test_hash_dir_not_found(self):
        self.provideFile("test")
        self.assertRaisesRegex(
            ValueError,
            "The given path .* is not a directory",
            client.shorthand.hash_directory,
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
