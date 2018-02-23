"""
This module contains tests for the logger.py module.
"""
import random
import string

from unittest import TestCase

from time import sleep

from os.path import isdir, join
from os import mkdir, getcwd, listdir, rmdir

from shutil import rmtree

from uuid import uuid4

from datetime import datetime

from client import logger
from client.logger import ClientLogger


class TestLogger(TestCase):
    FOLDER = join(
        getcwd(),
        'logs',
    )

    @classmethod
    def setUpClass(cls):
        super(TestLogger, cls).setUpClass()
        if not isdir(cls.FOLDER):
            mkdir(cls.FOLDER)

    def setUp(self):
        rmtree(self.FOLDER)
        mkdir(self.FOLDER)

    def test_no_preexisting_logfolder(self):
        rmtree(self.FOLDER)
        new_logger = ClientLogger()
        new_logger.enable()
        new_logger.disable()

        dirs = listdir(self.FOLDER)
        self.assertEqual(1, len(dirs))

    def test_multiple_preexisting_logfolders(self):
        dir_1 = datetime.now().strftime(ClientLogger.DATE_FORMAT)
        sleep(0.1)
        dir_2 = datetime.now().strftime(ClientLogger.DATE_FORMAT)
        sleep(0.1)
        dir_3 = datetime.now().strftime(ClientLogger.DATE_FORMAT)

        mkdir(join(self.FOLDER, dir_1))
        mkdir(join(self.FOLDER, dir_2))
        mkdir(join(self.FOLDER, dir_3))

        sleep(0.1)
        logger.LOGGER.enable()
        logger.LOGGER.disable()

        dirs = listdir(self.FOLDER)
        self.assertEqual(2, len(dirs))
        self.assertNotIn(dir_1, dirs)
        self.assertNotIn(dir_2, dirs)
        self.assertIn(dir_3, dirs)

    def test_unknown_preexisting_logfolders(self):
        dir_unknown = 'unknown'
        dir_1 = datetime.now().strftime(ClientLogger.DATE_FORMAT)
        sleep(0.1)
        dir_2 = datetime.now().strftime(ClientLogger.DATE_FORMAT)

        mkdir(join(self.FOLDER, dir_1))
        mkdir(join(self.FOLDER, dir_2))
        mkdir(join(self.FOLDER, dir_unknown))

        sleep(0.1)
        logger.LOGGER.enable()
        logger.LOGGER.disable()

        dirs = listdir(self.FOLDER)
        self.assertEqual(3, len(dirs))
        self.assertNotIn(dir_1, dirs)
        self.assertIn(dir_2, dirs)

        rmdir(join(self.FOLDER, dir_unknown))

    def test_add_program_logger(self):
        uuid = uuid4().hex
        logger.LOGGER.add_program_logger(
            random.choice(string.digits), uuid, '{}.log'.format(uuid), 100)
        self.assertIn(uuid, logger.LOGGER.program_loggers)
