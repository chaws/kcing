#/usr/bin/env python3

import unittest
import logging
import os
import shutil

import samples


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class fake_args(object):
    pass

class TestSamples(unittest.TestCase):

    def setUp(self):
        self.test_dir = '/tmp/kcing_test'
        os.makedirs(self.test_dir, exist_ok=True)

        self.args = fake_args()

        self.builds = {'1': 'https://linaro.org', '2': 'https://lajlsjf234.com'}

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_is_samples_dir_ok(self):
        self.assertFalse(samples._is_samples_dir_ok('/root'))
        self.assertTrue(samples._is_samples_dir_ok(self.test_dir))

    def test_persist_samples(self):
        saved, failed = samples._persist_samples('build', self.builds, self.test_dir)
        files = os.listdir(self.test_dir)

        self.assertEqual(len(saved), 1)
        self.assertEqual(saved, {'1': 'build_1.json'})
        self.assertEqual(failed, {'2': 'https://lajlsjf234.com'})
        self.assertEqual(len(files), 1)
        self.assertEqual(files, ['build_1.json'])

    def test_gen(self):
        self.args.sample_size = 1
        self.args.samples_dir = self.test_dir
        rc = samples.gen(self.args)
        files = os.listdir(self.test_dir).sort()

        self.assertEqual(rc, 0)
        

def main():
    unittest.main()

if __name__ == '__main__':
    main()

