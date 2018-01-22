import unittest
import asyncio
import os
import shutil

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

    def test_move_file_with_file(self):
        file_name = "testfile.txt"
        if os.path.isfile(file_name):
            os.remove(file_name)
        myfile_name = "testfile_link.txt"
        if os.path.isfile(myfile_name):
            os.remove(myfile_name)

        open(file_name, "w").close()
        self.loop.run_until_complete(
            client.command.move_file(file_name, myfile_name))
        self.assertTrue(os.path.isfile(myfile_name))
        os.remove(file_name)
        os.remove(myfile_name)

    def test_move_file_with_dir(self):
        file_name = 'file.txt'
        source = os.path.abspath('./sourcefolder/')
        if not os.path.isdir(source):
            os.makedirs(source)
        dest = os.path.abspath('./destfolder/')
        if not os.path.isdir(dest):
            os.makedirs(dest)

        open(os.path.join(source, file_name), "w").close()

        self.loop.run_until_complete(client.command.move_file(source, dest))
        self.assertTrue(
            os.path.isfile(
                os.path.join(dest, os.path.join(source, file_name))))

        shutil.rmtree(source)
        shutil.rmtree(dest)

    def test_move_file_wrong_sourcePath_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.move_file(1, "file.txt"),
        )

    def test_move_file_wrong_destinationPath_object(self):
        self.assertRaises(
            ValueError,
            self.loop.run_until_complete,
            client.command.move_file("file.txt", 1),
        )
    """
    def test_move_file_backup_exists_error_file(self):
        file_name = os.path.abspath("file.txt")
        if os.path.isfile(file_name):
            os.remove(file_name)
        myfile_name = os.path.abspath("dest.txt")
        if os.path.isfile(myfile_name):
            os.remove(myfile_name)
        back_file_name = os.path.abspath("dest.txt_BACK")
        if os.path.isfile(back_file_name):
            os.remove(back_file_name)

        open(file_name, "w").close()
        open(myfile_name, "w").close()
        open(back_file_name, "w").close()
        self.assertRaises(
            FileExistsError,
            self.loop.run_until_complete,
            client.command.move_file(file_name, myfile_name),
        )
        os.remove(file_name)
        os.remove(myfile_name)
        os.remove(back_file_name)

    def test_move_file_backup_exists_error_dir(self):
        file_name = 'file.txt'
        back = '_BACK'
        source = os.path.abspath('./sourcefolder2/')
        dest = os.path.abspath('./destfolder2/')
        dest_dir = os.path.abspath('./destfolder2/sourcefolder2')
        dest_back = os.path.abspath('./destfolder2/sourcefolder2' + back)

        if not os.path.isdir(source):
            os.makedirs(source)
        if not os.path.isdir(dest):
            os.makedirs(dest)
        if not os.path.isdir(dest_back):
            os.makedirs(dest_back)
        if not os.path.isdir(dest_dir):
            os.makedirs(dest_dir)

        open(os.path.join(source, file_name), "w").close()

        self.assertRaises(
            FileExistsError,
            self.loop.run_until_complete,
            client.command.move_file(source, dest),
        )
        shutil.rmtree(source)
        shutil.rmtree(dest)
    """
    def test_move_file_source_does_not_exist(self):
        self.assertRaises(
            FileNotFoundError,
            self.loop.run_until_complete,
            client.command.move_file("source.txt", "dest.txt"),
        )

    def test_move_file_destination_not_directory(self):
        file_name = 'file.txt'
        source = os.path.abspath('./sourcefolder3/')
        if not os.path.isdir(source):
            os.makedirs(source)
        dest = os.path.abspath('./destfolder3/')
        if not os.path.isdir(dest):
            os.makedirs(dest)

        open(os.path.join(source, file_name), "w").close()
        open(os.path.join(dest, file_name), 'w').close()

        self.assertRaises(
            NotADirectoryError,
            self.loop.run_until_complete,
            client.command.move_file(source, os.path.join(dest, file_name)),
        )
        shutil.rmtree(source)
        shutil.rmtree(dest)

    def test_online(self):
        result = self.loop.run_until_complete(client.command.online())
        self.assertIsNone(result)

    def test_cancel_execution(self):
        if os.name == 'nt':
            prog = "C:\\Windows\\System32\\cmd.exe"
            args = ["/c", "TIMEOUT 10>nul"]
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

        self.assertTrue('Process got canceled and returned' in
                        self.loop.run_until_complete(create_and_cancel_task()))
