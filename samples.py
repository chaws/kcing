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


def _is_samples_dir_ok(samples_dir):
    # Make sure samples folder exists and is writable
    logger.debug('Checking if %s is exists and is writable' % (samples_dir))
    try:
        pathlib.Path(samples_dir).mkdir(exist_ok=True)
        if not os.access(samples_dir, os.W_OK):
            logger.error('"%s" needs to be writable!' % (samples_dir))
            return False
    except PermissionError:
        logger.error('Permission denied to create "%s"' % (samples_dir))
        return False

    return True


def _persist_samples(sample_type, objs, samples_dir):
    if len(objs) == 0:
        logger.warning('Persisting %s skipped due to empty list of objects' % (sample_type))
        return {}, {}

    failed = {}
    saved = {}
    for _id in objs.keys():
        download_link = objs[_id]
        try:
            logger.debug('Downloading "%s"' % (download_link))
            response = _client().get(download_link)
        except:
            logger.error('Failed to download "%s" due to connection issues' % (download_link))
            failed[_id] = download_link
            continue

        if response.status_code != 200:
            logger.error('Failed to download "%s" due to HTTP response: status_code = %i' % (download_link, response.status_code))
            failed[_id] = download_link
            continue
        
        file_name = '%s_%s.json' % (sample_type, _id)
        file_content = response.content.decode()
        with open('%s/%s' % (samples_dir, file_name), 'w') as file_handler:
            file_handler.write(file_content)
            logger.debug('Written %i bytes to %s' % (len(file_content), file_name))
            saved[_id] = file_name

    return saved, failed


def gen(args):
    """
    Download last two days worth of builds and lavas from kernelci
    """

    logger.info('Generating sample data')

    samples_dir = args.samples_dir or SAMPLES_DIR

    if not _is_samples_dir_ok(samples_dir):
        return -1

    kci = KernelCI()

    lavas = kci.get_lavas(how_many=args.sample_size)
    builds = kci.get_builds(how_many=args.sample_size)

    logger.info('Retrieved %i lavas and %i builds from KernelCI' % (len(lavas), len(builds)))

    saved_lavas, failed_lavas = _persist_samples('lava', lavas, samples_dir)
    saved_builds, failed_builds = _persist_samples('build', builds, samples_dir)

    logger.info('Lavas: saved %i to disk, %i failed' % (len(saved_lavas), len(failed_lavas.keys())))
    logger.info('Builds: saved %i to disk, %i failed' % (len(saved_builds), len(failed_builds.keys())))

    return 0
