#!/usr/bin/env python3

import argparse
import logging
import sys

import elastic
import logstash
import models
import samples
import tests
import settings


logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s@%(funcName)s: %(message)s')

# Consoler logger
stdout_logger = logging.StreamHandler()
stdout_logger.setLevel(logging.INFO)
stdout_logger.setFormatter(log_format)
logger.addHandler(stdout_logger)


avail_cmds = {
    'test': tests.run,
    'feed_es': elastic.feed,
    'gen_samples': samples.gen,
    'setup_ls': logstash.setup,
    'drp': models.drp,
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
    parser.add_argument("cmd", choices=avail_cmds.keys(),
                        help="`test` runs available tests; use --testargs to provide extra args for unittest. "
                             "`gen_samples` generates --sample-size (or past two days of) boots and builds from kernelci and save it to --samples-dir. "
                             "`setup_ls` configures logstash to better use queueing. "
                             "`feed_es` downloads boots/builds from kernelci and submit them to ES. "
                             "`drp` removes old local helper boots/builds stored locally"
    )
    parser.add_argument("-l", "--log-filename",
                        help="Logging file name")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="Debugging log level")
    parser.add_argument("--how-many", type=int, default=-1,
                        help="How many boots and builds to feed ES, defaults to two past days worth of data")
    parser.add_argument("--boots", nargs='+',
                        help="List of boot files to send to ES")
    parser.add_argument("--builds", nargs='+',
                        help="List of build files to send to ES")
    parser.add_argument("--sample-size", type=int, default=-1,
                        help="How many samples to download, defaults to two past days worth of data")
    parser.add_argument("--samples-dir", default='samples',
                        help="Directory to where samples are going to be stored, defaults to `samples`")
    parser.add_argument("--drp-days", type=int, default=settings.DRP_DAYS,
                        help="Apply data retention policy to delete objects older than '--drp-days' days")
    parser.add_argument("-t", "--testargs", nargs='*',
                        help="Unittest args")
    args = parser.parse_args()

    sys.exit(main(args))
