"""
This module contains a class which manages logging.
"""
import logging
import asyncio

from sys import stdout

from os import listdir, mkdir, getcwd
from os.path import join, isdir
from pathlib import PurePath

from asyncio import Future

from random import randrange

from shutil import rmtree

from datetime import datetime


class ProgramLogger:
    """
    class used for logging one program
    """

    def __init__(self, path, port, max_file_size):
        self.__port = port
        self.__pid = 0
        self.__path = path
        self.__max_file_size = max_file_size

    @property
    def pid(self):
        return self.__pid

    @property
    def port(self):
        return self.__port

    @asyncio.coroutine
    def run(self):
        finished = Future()

        @asyncio.coroutine
        def handle_connection(reader, writer):
            pid = yield from reader.readline()
            self.__pid = int(pid)
            with open(self.__path, mode='wb') as logfile:
                while not reader.at_eof():
                    buffer = yield from reader.read(1)
                    logfile.write(buffer)
                    # log to websocket if enabled
            writer.close()
            finished.set_result(True)

        server_coroutine = asyncio.start_server(
            handle_connection,
            '127.0.0.1',
            self.__port,
            loop=asyncio.get_event_loop(),
        )
        server = yield from asyncio.get_event_loop().create_task(
            server_coroutine)
        yield from finished
        server.close()
        yield from server.wait_closed()

    def get_log(self):
        with open(self.__path, mode='rb') as logfile:
            data = logfile.read()
            return data

    def enable_remote(self):
        pass
        # connect websocket
        # block logging
        # send existing log over websocket
        # enable logging over websocket
        # unblock logging


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

        if not isdir(join(getcwd(), 'logs')):
            mkdir('logs')

    def add_program_logger(self, uuid, file_name, max_file_size):
        while True:
            try:
                port = randrange(49152, 65535)
                self.__program_loggers[uuid] = ProgramLogger(
                    join(self.__logdir, file_name),
                    port,
                    max_file_size,
                )
                break
            except OSError as err:
                if err.errno is 98:  # port allready in use
                    pass
                else:
                    raise err

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
