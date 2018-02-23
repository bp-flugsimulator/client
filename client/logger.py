"""
This module contains a class which manages logging.
"""
import logging
import asyncio

from sys import stdout

from os import listdir, mkdir, getcwd, rename
from os.path import join, isdir, isfile
import websockets

from asyncio import Future, Event
from threading import Lock

from random import randrange

from shutil import rmtree

from datetime import datetime

from utils import Status


class RotatingFile:
    def __init__(self, path, max_file_size=(1 << 20), mode='wb'):
        self.__path = path
        self.__max_file_size = max_file_size
        self.__mode = mode
        self.__pos = 0
        self.__file = open(path, mode=mode)

    def write(self, input):
        if self.__pos < self.__max_file_size:
            self.__pos += 1
        else:
            self.__file.close()
            rename(self.__path, '{}.1'.format(self.__path))
            self.__file = open(self.__path, mode=self.__mode)
            self.__pos = 0

        self.__file.write(input)

    def flush(self):
        self.__file.flush()

    def close(self):
        self.__file.close()


class ProgramLogger:
    """
    class used for logging one program
    """

    def __init__(self, pid_on_master, path, port, max_file_size, url):
        self.__port = port
        self.__pid = 0
        self.__pid_on_master = pid_on_master
        self.__path = path
        self.__max_file_size = max_file_size
        self.__url = url
        self.__ws_connection = None
        self.__ws_buffer = b''
        self.__ws_buffer_has_content = Event(loop=asyncio.get_event_loop())
        self.__lock = Lock()

    @property
    def pid(self):
        return self.__pid

    @property
    def port(self):
        return self.__port

    @asyncio.coroutine
    def run(self):
        finished = Event(loop=asyncio.get_event_loop())

        @asyncio.coroutine
        def handle_connection(reader, writer):
            pid = yield from reader.readline()
            self.__pid = int(pid)
            log_file = RotatingFile(self.__path, self.__max_file_size)

            while not reader.at_eof():
                buffer = yield from reader.read(1)
                with self.__lock:
                    log_file.write(buffer)
                    log_file.flush()
                    if self.__ws_connection:
                        self.__ws_buffer += buffer
                        self.__ws_buffer_has_content.set()

            log_file.close()
            writer.close()
            finished.set()

        server_coroutine = asyncio.start_server(
            handle_connection,
            '127.0.0.1',
            self.__port,
            loop=asyncio.get_event_loop(),
        )
        server = yield from asyncio.get_event_loop().create_task(
            server_coroutine)
        yield from finished.wait()
        server.close()
        yield from server.wait_closed()

    @asyncio.coroutine
    def enable_remote(self):
        self.__ws_connection = yield from websockets.connect(self.__url)
        with self.__lock:
            with open(self.__path, mode='rb') as logfile:
                data = logfile.read()
                data = data.decode()
                message = {'log': data, 'pid': self.__pid_on_master}
                status = Status.ok(message)

        yield from self.__ws_connection.send(status.to_json())
        yield from self.__ws_connection.recv()

        while True:
            yield from self.__ws_buffer_has_content.wait()
            with self.__lock:
                message = {
                    'log': self.__ws_buffer.decode(),
                    'pid': self.__pid_on_master
                }
                self.__ws_buffer = b''
                self.__ws_buffer_has_content.clear()
            try:
                yield from self.__ws_connection.send(
                    Status.ok(message).to_json())
                yield from self.__ws_connection.recv()
            except websockets.exceptions.ConnectionClosed:
                break

            if message['log'] == b''.decode():
                break

    @asyncio.coroutine
    def disable_remote(self):
        with self.__lock:
            yield from self.__ws_connection.close()

    def get_log(self):
        data = b''
        with open(self.__path, mode='rb') as logfile:
            data = logfile.read()

        if isfile(self.__path + '.1'):
            with open(self.__path, mode='rb') as logfile:
                data += logfile.read()

        return data


class ClientLogger:
    """
    class used to manage logging
    """
    DATE_FORMAT = '%H.%M.%S.%f-%d.%m.%Y'

    @property
    def logdir(self):
        """
        Getter method for the current directory
        where the logs are stored

        Return
        ------
            str
        """
        return self.__logdir

    def __init__(self):
        self.__logdir = join(getcwd(), 'logs',
                             datetime.now().strftime(self.DATE_FORMAT))
        self.__enabled = False
        self.__file_ch = None
        self.__stream_ch = None
        self.__program_loggers = dict()
        self.__url = None

        if not isdir(join(getcwd(), 'logs')):
            mkdir('logs')

    def add_program_logger(self, pid, uuid, file_name, max_file_size):
        while True:
            try:
                port = randrange(49152, 65535)
                self.__program_loggers[uuid] = ProgramLogger(
                    pid,
                    join(self.__logdir, file_name),
                    port,
                    max_file_size,
                    self.__url,
                )
                break
            except OSError as err:
                if err.errno is 98:  # port allready in use
                    pass
                else:
                    raise err

    @property
    def url(self):
        return self.__url

    @url.setter
    def url(self, url):
        self.__url = url

    @property
    def program_loggers(self):
        return self.__program_loggers

    def enable(self):
        """
        Removes all logging folders except the last one. Then creates a new
        logging folder and starts logging into it.
        """
        if not self.__enabled:
            self.__enabled = True

            print('initializing log folder')
            dates = []
            for entry in listdir(join(getcwd(), 'logs')):
                if isdir(join('logs', entry)):
                    try:
                        dates.append(
                            datetime.strptime(entry, self.DATE_FORMAT))
                    except ValueError:
                        pass
            dates.sort()
            for date in dates[:-1]:
                rmtree(join(getcwd(), 'logs', date.strftime(self.DATE_FORMAT)))
                print('deleted logs from {}'.format(
                    date.strftime(self.DATE_FORMAT)))

            self.__logdir = join(getcwd(), 'logs',
                                 datetime.now().strftime(self.DATE_FORMAT))
            mkdir(self.logdir)

            print('enable logger')
            root = logging.getLogger()
            root.setLevel(logging.DEBUG)

            self.__file_ch = logging.FileHandler(
                join(self.logdir, 'client.log'))
            self.__stream_ch = logging.StreamHandler(stdout)

            self.__file_ch.setLevel(logging.DEBUG)
            self.__stream_ch.setLevel(logging.DEBUG)

            formatter = logging.Formatter(
                "[CLIENT] [%(asctime)s]: %(message)s",
                datefmt='%M:%S',
            )
            self.__file_ch.setFormatter(formatter)
            self.__stream_ch.setFormatter(formatter)

            root.addHandler(self.__file_ch)
            root.addHandler(self.__stream_ch)

    def disable(self):
        """
        Disables logging.
        """
        if self.__enabled:
            self.__enabled = False

            print('disable logger')
            root = logging.getLogger()
            root.removeHandler(self.__file_ch)
            root.removeHandler(self.__stream_ch)

            self.__file_ch.flush()
            self.__stream_ch.flush()

            self.__file_ch.close()
            self.__stream_ch.close()


LOGGER = ClientLogger()
