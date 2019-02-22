#!/usr/bin/env python3

import logging
import sys

import test_kernelci


logger = logging.getLogger()


def run(args):
    testargs = args.testargs or ['test_kernelci.TestKernelCIMethods']
    sys.argv[1:] = testargs
    return test_kernelci.main()
