#/usr/bin/env python3

import unittest
import logging
import os
import shutil
import tempfile

from os.path import join, isfile

import elastic as es
import models
import settings


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class fake_args(object):
    pass

class TestElastic(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.dir.cleanup()

    def test_load_leftovers(self):
        os.mknod(join(self.dir.name, 'boot_1.json'))
        os.mknod(join(self.dir.name, 'build_1.json'))
        leftovers = es._load_leftovers(self.dir.name)

        self.assertEqual(len(leftovers['boot']), 1)
        self.assertEqual(len(leftovers['build']), 1)
        self.assertEqual(leftovers['boot'], {'1': 'boot_1.json'})
        self.assertEqual(leftovers['build'], {'1': 'build_1.json'})

    def test_download(self):
        downloads = es._download('boot', {'1': 'https://linaro.org'}, self.dir.name)
        self.assertEqual(len(downloads), 1)
        self.assertEqual(downloads, {'1': 'boot_1.json'})

        downloads = es._download('build', {'1': 'https://linaro.org'}, self.dir.name)
        self.assertEqual(len(downloads), 1)
        self.assertEqual(downloads, {'1': 'build_1.json'})

        leftovers = es._load_leftovers(self.dir.name)

        self.assertEqual(len(leftovers['boot']), 1)
        self.assertEqual(len(leftovers['build']), 1)
        self.assertEqual(leftovers['boot'], {'1': 'boot_1.json'})
        self.assertEqual(leftovers['build'], {'1': 'build_1.json'})

    def test_is_data_dir_ok(self):
        self.assertTrue(es._is_data_dir_ok(self.dir.name))
        self.assertFalse(es._is_data_dir_ok('/root/lala456nonexistant'))

    def test_is_es_ok(self):
        self.assertTrue(es._is_es_ok())

    def test_unlink_successfull_objs(self):
        file_name = join(self.dir.name, 'boot_1.json')
        os.mknod(file_name)
        self.assertTrue(isfile(file_name))
        es._unlink_successfull_objs({'1': 'boot_1.json'}, self.dir.name)
        self.assertFalse(isfile(file_name))

    def test_post(self):
        file_name = join(self.dir.name, 'boot_1.json')
        os.mknod(file_name)
        self.assertTrue(isfile(file_name))

        response = es._post('boot', 'boot_1.json', self.dir.name)
        self.assertTrue(response)

        response = es._post('boot', 'does_not_exist', self.dir.name)
        self.assertFalse(response)

    def test_send(self):
        file_name = join(self.dir.name, 'boot_1.json')
        os.mknod(file_name)
        self.assertTrue(isfile(file_name))

        response = es._send('boot', 'boot_1.json', self.dir.name)
        self.assertTrue(response)

        response = es._send('boot', 'does_not_exist', self.dir.name)
        self.assertFalse(response)

    def test_send_to_es(self):
        file_name = join(self.dir.name, 'boot_1.json')
        os.mknod(file_name)
        self.assertTrue(isfile(file_name))

        passed, failed = es._send_to_es('boot', {'1': 'boot_1.json'}, self.dir.name)
        self.assertEqual(len(passed), 1)
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(models.all_objs('boot')), 1)
        self.assertFalse(isfile(file_name))
        

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
    models.init()
    models.create_tables()

    rc = unittest.main()

    models.end()

    return rc

if __name__ == '__main__':
    main()

