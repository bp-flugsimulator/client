"""
This module contains tests for the logger.py module.
"""
import random
import string

from unittest import TestCase

from time import sleep

from os.path import isdir, join
from os import mkdir, getcwd, listdir, rmdir, remove

from shutil import rmtree

from uuid import uuid4

from datetime import datetime

from client import logger
from client.logger import ClientLogger, RotatingFile


class TestRotatingFile(TestCase):
    PATH = None

    def setUp(self):
        self.PATH = join(getcwd(), '{}.log'.format(''.join([
            random.choice(string.digits + string.ascii_letters)
            for _ in range(10)
        ])))

    def tearDown(self):
        try:
            remove(self.PATH)
            remove('{}.1'.format(self.PATH))
        except FileNotFoundError:
            pass

    def test_small_data_on_opened_file(self):
        content = ''.join([
            random.choice(string.digits + string.ascii_letters)
            for _ in range(100)
        ])
        file = RotatingFile(self.PATH, mode='w+')
        file.write(content)
        self.assertEqual(content, file.read())
        file.close()

    def test_small_data_on_closed_file(self):
        content = ''.join([
            random.choice(string.digits + string.ascii_letters)
            for _ in range(100)
        ])
        file = RotatingFile(self.PATH, mode='w+')
        file.write(content)
        file.close()
        self.assertEqual(content, file.read())

    def test_big_data_on_opened_file(self):
        content_1 = ''.join([
            random.choice(string.digits + string.ascii_letters)
            for _ in range(500)
        ])
        content_2 = ''.join([
            random.choice(string.digits + string.ascii_letters)
            for _ in range(500)
        ])
        file = RotatingFile(self.PATH, max_file_size=500, mode='w+')
        file.write(content_1)
        file.write(content_2)
        self.assertEqual(content_1 + content_2, file.read())
        file.close()

    def test_big_data_on_closed_file(self):
        content_1 = ''.join([
            random.choice(string.digits + string.ascii_letters)
            for _ in range(500)
        ])
        content_2 = ''.join([
            random.choice(string.digits + string.ascii_letters)
            for _ in range(500)
        ])
        file = RotatingFile(self.PATH, max_file_size=500, mode='w+')
        file.write(content_1)
        file.write(content_2)
        file.close()
        self.assertEqual(content_1 + content_2, file.read())


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
        logger.LOGGER.enable()
        logger.LOGGER.url = 'localhost:8050'
        uuid = uuid4().hex
        print(uuid)
        logger.LOGGER.add_program_logger(
            random.choice(string.digits), uuid, '{}.log'.format(uuid), 100)
        self.assertIn(uuid, logger.LOGGER.program_loggers)
        self.assertEqual('localhost:8050', logger.LOGGER.url)
        logger.LOGGER.disable()
