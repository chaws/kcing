#/usr/bin/env python3

import unittest
import logging

from kernelci import KernelCI, CannotContinue


logger = logging.getLogger()


class TestKernelCIMethods(unittest.TestCase):

    def setUp(self):
        self.kci = KernelCI(max_retries=1, max_per_req=1)

    def test_http(self):
        response = self.kci._http('https://google.com')
        self.assertEqual(response.status_code, 200)

        with self.assertRaises(CannotContinue):
            self.kci._http('http://non123existing456url.dot.com')

        # Make sure when blocking=False, no exception is raises
        self.kci._http('http://non123existing456url.dot.com', blocking=False)
        
    def test_refresh_csrf_token(self):
        token = self.kci._refresh_csrf_token()
        self.assertNotEqual(len(token), 0)

    def test_get_docs(self):
        lavas = self.kci._get_docs('lava', how_many=1)
        self.assertEqual(len(lavas), 1)

        builds = self.kci._get_docs('build', how_many=1)
        self.assertEqual(len(builds), 1)

    def test_get_lavas(self):
        links = self.kci.get_lavas(how_many=1)
        self.assertEqual(len(links), 1)

    def test_get_builds(self):
        links = self.kci.get_builds(how_many=1)
        self.assertEqual(len(links), 1)

def main():
    unittest.main()

if __name__ == '__main__':
    main()
