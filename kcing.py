#!/usr/bin/env python3

import argparse
import logging
import sys

import test_kernelci
import samples


logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s@%(funcName)s: %(message)s')

# Consoler logger
stdout_logger = logging.StreamHandler()
stdout_logger.setLevel(logging.INFO)
stdout_logger.setFormatter(log_format)
logger.addHandler(stdout_logger)


def test(args):
    testargs = args.testargs or ['test_kernelci.TestKernelCIMethods']
    sys.argv[1:] = testargs
    return test_kernelci.main()


def feed_es(args):
    logger.info('Feeding ES')


def gen_samples(args):
    logger.info('Generating sample data')
    samples.gen(args)


avail_cmds = {
    'test': test,
    'feed_es': feed_es,
    'gen_samples': gen_samples,
}


def main(args):
    if args.log_filename:
        file_logger = logging.FileHandler(args.log_filename)
        file_logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
        file_logger.setFormatter(log_format)
        logger.addHandler(file_logger)

    if args.debug:
        logger.setLevel(logging.DEBUG)
        stdout_logger.setLevel(logging.DEBUG)
        logger.debug('Debugging is on!')

    # Call
    func = avail_cmds[args.cmd]
    return func(args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=['test', 'feed_es', 'gen_samples'],
                        help="command")
    parser.add_argument("-l", "--log-filename",
                        help="logging file name")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="debugging log level")
    parser.add_argument("--sample-size", type=int, default=-1,
                        help="how many samples to download, defaults to two past days worth of data")
    parser.add_argument("-t", "--testargs", nargs='*',
                        help="unittest args")
    args = parser.parse_args()

    sys.exit(main(args))
