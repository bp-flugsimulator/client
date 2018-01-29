"""
This module contains tests for the logger.py module.
"""
from unittest import TestCase

from time import sleep

from os.path import isdir, join
from os import mkdir, getcwd, listdir, rmdir

from shutil import rmtree

from datetime import datetime

from client import logger
from client.logger import ClientLogger


class TestCommands(TestCase):
    FOLDER = join(
        getcwd(),
        'logs',
    )

    @classmethod
    def setUpClass(cls):
        super(TestCommands, cls).setUpClass()
        if not isdir(cls.FOLDER):
            mkdir(cls.FOLDER)

    def setUp(self):
        rmtree(self.FOLDER)
        mkdir(self.FOLDER)

    def test_multiple_preexisting_logfolders(self):
        dir_1 = datetime.now().strftime(ClientLogger.DATE_FORMAT)
        sleep(0.1)
        dir_2 = datetime.now().strftime(ClientLogger.DATE_FORMAT)
        sleep(0.1)
        dir_3 = datetime.now().strftime(ClientLogger.DATE_FORMAT)

        mkdir(join(self.FOLDER, dir_1))
        mkdir(join(self.FOLDER, dir_2))
        mkdir(join(self.FOLDER, dir_3))

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

        logger.LOGGER.enable()
        logger.LOGGER.disable()

        dirs = listdir(self.FOLDER)
        self.assertEqual(3, len(dirs))
        self.assertNotIn(dir_1, dirs)
        self.assertIn(dir_2, dirs)

        rmdir(join(self.FOLDER, dir_unknown))
