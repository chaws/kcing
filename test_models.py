#/usr/bin/env python3

import unittest
import logging
import os
import shutil

import settings
from models import init, end, create_tables, all_objs, save, delete_old


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TestModels(unittest.TestCase):

    def setUp(self):
        builds = {'1': 'build1', '2': 'build2'}
        lavas = {'1': 'boot1', '2': 'boot2', '3': 'boot3'}
        save('build', builds)
        save('lava', lavas)

    def tearDown(self):
        delete_old(0)

    def test_all_objs(self):
        lavas = all_objs('lava')
        builds = all_objs('build')

        self.assertEqual(len(lavas), 3)
        self.assertEqual(len(builds), 2)

    def test_delete_old(self):
        delete_old(0)

        lavas = all_objs('lava')
        builds = all_objs('build')

        self.assertEqual(len(lavas), 0)
        self.assertEqual(len(builds), 0)

def main():
    if 'test' not in settings.KCING_DB:
        logger.error('Database for testing should contain the word "test" in it')
        logger.error('Please specify a testing database passing KCING_DB env var when running tests')
        return -1

    # Deletes current db to make sure we're working with a fresh one
    try:
        os.unlink(settings.KCING_DB)
    except OSError:
        pass

    os.mknod(settings.KCING_DB)
    init()
    create_tables()

    rc = unittest.main()

    end()

    return rc
    

if __name__ == '__main__':
    main()
