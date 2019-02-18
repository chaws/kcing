#!/usr/bin/env python3

import argparse
import logging
import sys


import test_kernelci


logger = logging.getLogger()
log_format = logging.Formatter('%(asctime)s - %(filename)s:%(funcName)s - %(levelname)s: %(message)s')
log_level = logging.INFO

# Consoler logger
stdout_logger = logging.StreamHandler()
stdout_logger.setLevel(log_level)
stdout_logger.setFormatter(log_format)
logger.addHandler(stdout_logger)


def test(args):
    testargs = args.testargs or ['test_kernelci.TestKernelCIMethods']
    sys.argv[1:] = testargs
    return test_kernelci.main()


def feed_es(args):
    logger.info('Feeding ES')


def main(args):
    global log_level

    if args.debug:
        log_level = logging.DEBUG
        logger.setLevel(log_level)
    
    if args.log_filename:
        file_logger = logging.FileHandler(args.log_filename)
        file_logger.setLevel(log_level)
        file_logger.setFormatter(log_format)
        logger.addHandler(file_logger)


    if args.cmd == 'test':
        return test(args)
    elif args.cmd == 'feed_es':
        return feed_es(args)

    # Unknown state
    return -1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=['test', 'feed_es'],
                        help="command")
    parser.add_argument("-l", "--log-filename",
                        help="logging file name")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="debugging log level")
    parser.add_argument("-t", "--testargs", nargs='*',
                        help="unittest args")
    args = parser.parse_args()

    sys.exit(main(args))
