import unittest
import importlib
import asyncio

from utils import Rpc
import client.command


class TestCommands(unittest.TestCase):
    def test_all_functions_in_rpc(self):
        """
        Tests if all functions in commands are set with Rpc flag.
        """
        import types
        for func in dir(client.command):
            if isinstance(getattr(client.command, func), types.FunctionType):
                self.assertEqual(getattr(client.command, func), Rpc.get(func))

    def test_uptime(self):
        loop = asyncio.get_event_loop()
        time = loop.run_until_complete(client.command.uptime(0))
        uptime_time = float(time['uptime'])
        uptime_sid = int(time['sid'])
        self.assertEqual(uptime_sid, 0)
        self.assertTrue(isinstance(time['sid'], int))

    def test_boottime(self):
        import datetime
        loop = asyncio.get_event_loop()
        time = loop.run_until_complete(client.command.boottime(0))
        boottime_time = datetime.datetime.strptime(time['boottime'],
                                                   "%Y-%m-%d %X")
        boottime_sid = int(time['sid'])
        self.assertEqual(boottime_sid, 0)
        self.assertTrue(isinstance(time['sid'], int))

    def test_execution_wrong_path_object(self):
        loop = asyncio.get_event_loop()
        self.assertRaises(
            ValueError,
            loop.run_until_complete,
            client.command.execute(0, "calc.exe", "this is a arguments list"),
        )

    def test_execution_wrong_prog_object(self):
        loop = asyncio.get_event_loop()
        self.assertRaises(
            ValueError,
            loop.run_until_complete,
            client.command.execute(0, ["calc.exe"], []),
        )

    def test_execution_wrong_arguments_elements(self):
        loop = asyncio.get_event_loop()
        self.assertRaises(
            ValueError,
            loop.run_until_complete,
            client.command.execute(0, "calc.exe", [1, 2, 34]),
        )

    def test_execution_not_existing_prog(self):
        loop = asyncio.get_event_loop()
        self.assertRaises(
            FileNotFoundError,
            loop.run_until_complete,
            client.command.execute(0, "calc.exe", []),
        )

    def test_execution_echo_shell(self):
        import os

        if os.name == 'nt':
            prog = "C:\\Windows\\System32\\cmd.exe"
            args = ["/c", "ECHO %date%"]
        else:
            prog = "/bin/sh"
            args = ["-c", "echo $(date)"]

        loop = asyncio.get_event_loop()
        result = {"code": 0, "method": "execute", "pid": 0}
        self.assertEqual(
            result,
            loop.run_until_complete(client.command.execute(0, prog, args)),
        )
