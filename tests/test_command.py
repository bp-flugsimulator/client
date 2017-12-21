import unittest
import asyncio
import os

from utils import Rpc
import client.command


class TestCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestCommands, cls).setUpClass()

        if os.name == 'nt':
            cls.loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(cls.loop)
        else:
            cls.loop = asyncio.get_event_loop()

    def test_all_functions_in_rpc(self):
        """
        Tests if all functions in commands are set with Rpc flag.
        """
        import types
        for func in dir(client.command):
            if isinstance(getattr(client.command, func), types.FunctionType):
                self.assertEqual(getattr(client.command, func), Rpc.get(func))

    def test_uptime(self):
        time = self.loop.run_until_complete(client.command.uptime(0))
        uptime_time = float(time['uptime'])
        uptime_sid = int(time['sid'])
        self.assertEqual(uptime_sid, 0)
        self.assertTrue(isinstance(time['sid'], int))

    def test_boottime(self):
        import datetime
        time = self.loop.run_until_complete(client.command.boottime(0))
        boottime_time = datetime.datetime.strptime(time['boottime'],
                                                   "%Y-%m-%d %X")
        boottime_sid = int(time['sid'])
        self.assertEqual(boottime_sid, 0)
        self.assertTrue(isinstance(time['sid'], int))

    def test_execution_wrong_path_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute(0, "calcs.exe", "this is a arguments list"),
        )

    def test_execution_wrong_prog_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute(0, ["calcs.exe"], []),
        )

    def test_execution_wrong_arguments_elements(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.execute(0, "calcs.exe", [1, 2, 34]),
        )

    def test_execution_not_existing_prog(self):
        self.assertRaises(
            FileNotFoundError,
            self.loop.run_until_complete,
            client.command.execute(0, "calcs.exe", []),
        )

    def test_execution_echo_shell(self):
        if os.name == 'nt':
            prog = "C:\\Windows\\System32\\cmd.exe"
            args = ["/c", "ECHO %date%"]
        else:
            prog = "/bin/sh"
            args = ["-c", "echo $(date)"]

        result = {"code": 0, "method": "execute", "pid": 0}
        self.assertEqual(
            result,
            self.loop.run_until_complete(
                client.command.execute(0, prog, args)),
        )
