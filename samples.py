#!/usr/bin/env python3

import os
import logging
import pathlib
import requests
from os.path import dirname, realpath, join

from kernelci import KernelCI

logger = logging.getLogger()
client = None
SAMPLES_DIR = join(dirname(realpath(__file__)), 'samples')


def _client():
    global client
    if client is None:
        client = requests.session()
        client.headers['Connection'] = 'keep-alive'

    return client


def _is_sample_dir_ok():
    # Make sure samples folder exists and is writable
    logger.debug('Checking if %s is exists and is writable' % (SAMPLES_DIR))
    try:
        pathlib.Path(SAMPLES_DIR).mkdir(exist_ok=True)
        if not os.access(SAMPLES_DIR, os.W_OK):
            logger.error('"%s" needs to be writable!')
            return False
    except PermissionError:
        logger.error('Permission denied to create "%s"')
        return False

    return True


def _persist_samples(sample_type, objs):
    if len(objs) == 0:
        logger.warning('Persisting %s skipped due to empty list of objects' % (sample_type))
        return

    failed = {}
    saved = 0
    for _id in objs.keys():
        download_link = objs[_id]
        try:
            response = _client().get(download_link)
        except:
            logger.error('Failed to download "%s"' % (download_link))
            failed[_id] = download_link
            continue
        
        file_name = '%s_%s.json' % (sample_type, _id)
        file_content = response.content.decode()
        with open('%s/%s' % (SAMPLES_DIR, file_name), 'w') as file_handler:
            file_handler.write(file_content)
            logger.debug('Written %i bytes to %s' % (len(file_content), file_name))
            saved += 1

    return saved, failed


def gen(args):
    """
    Download last two days worth of builds and boots from kernelci
    """

    if not _is_sample_dir_ok():
        return -1

    kci = KernelCI()

    boots = kci.get_boots(how_many=args.sample_size)
    builds = kci.get_builds(how_many=args.sample_size)

    logger.info('Retrieved %i boots and %i builds from KernelCI' % (len(boots), len(builds)))

    saved_boots, failed_boots = _persist_samples('boot', boots)
    saved_builds, failed_builds = _persist_samples('build', builds)

    logger.info('Boots: saved %i to disk, %i failed' % (saved_boots, len(failed_boots.keys())))
    logger.info('Builds: saved %i to disk, %i failed' % (saved_builds, len(failed_builds.keys())))

    return 0
