#!/usr/bin/env python3

# Takes Kernelci lavas/builds, send them to ES and save to a local sqlite
# db, data should not be duplicated in ES

import logging
import time
import requests
from os.path import isfile, isdir, dirname, join
from os import listdir, unlink, makedirs

import settings
import samples
import models
from kernelci import KernelCI

logger = logging.getLogger()

data_dir = join(dirname(__file__), 'data')
client = None
leftovers = None
es_lava_url = settings.ES_LAVA
es_build_url = settings.ES_BUILD


class fake_args(object):
    sample_size = -1


def _client():
    global client
    if client is None:
        client = requests.session()
        client.headers['Connection'] = 'keep-alive'

    return client


def _load_leftovers(path=data_dir):
    global leftovers
    leftovers = {'lava': {}, 'build': {}}
    for f in listdir(path):
        if f.startswith('lava_'):
            _type = 'lava'
        elif f.startswith('build_'):
            _type = 'build'
        else:
            continue

        _id = f.replace('%s_' % (_type), '').replace('.json', '')
        leftovers[_type][_id] = f

    return leftovers

def _download(_type, objs, path=data_dir):

    # Get whatever lava/build previously downloaded
    # but yet not successfully posted to ES
    _load_leftovers(path)
    downloads = leftovers[_type] # [_id] = (build|lava)_id.json
    logger.debug('%i %s files are already downloaded' % (len(downloads), _type))

    # Also, get a list of objects that were posted successfully
    processed = models.all_objs(_type)

    # Filter objs, removing ones already downloaded or processed
    fresh_ids = objs.keys() - downloads.keys()
    fresh_ids -= processed

    fresh_objs = {}
    for _id in fresh_ids:
        fresh_objs[_id] = objs[_id]

    logger.info('Downloading %i %s files' % (len(fresh_objs), _type))
    saved, failed = samples._persist_samples(_type, fresh_objs, path)

    # Merge recent downloads with leftover downloads
    logger.info('%i %s files successfully downloaded and %i failed' % (len(saved), _type, len(failed)))
    downloads.update(saved)
    return downloads


def _is_data_dir_ok(path=data_dir):
    try:
        makedirs(path, exist_ok=True)
        return True
    except PermissionError:
        logger.error('Permission denied to create "%s"' % (data_dir))
        return False


def _is_es_ok():
    logger.info('Checking ES health')

    for url in [es_lava_url, es_build_url]:
        try:
            response = _client().get(url)
        except:
            logger.error('Cannot reach "%s"' % (url))
            return False

        if response.status_code != 200:
            logger.error('GET "%s" did not return 200, instead returned %i' % (url, response.status_code))
            return False

        if response.content.decode() != 'ok':
            logger.error('GET "%s" did not return "ok", instead returned "%s"' % (url, response.content.decode()))
            return False

    logger.info('ES seems to be online')
    return True


def _unlink_successfull_objs(objs, path=data_dir):
    unlinked = 0
    for _id in objs.keys():
        try:
            unlink(join(path, objs[_id]))
            unlinked += 1
        except OSError as e:
            logger.error('Could not remove %s: %s' % (objs[_id], e))
    logger.info('Removed %i objects' % (unlinked))


def _post(_type, file_name, path=data_dir):
    if dirname(file_name) == '':
        file_name = join(path, file_name) 

    if not isfile(file_name):
        logger.error('Object %s is not a valid file' % (file_name))
        return False

    es_url = es_build_url if _type == 'build' else es_lava_url

    file_content = ''
    with open(file_name, 'r') as file_handler:
        file_content = file_handler.read()

    try:
        logger.debug('Sending %i bytes to %s' % (len(file_content), es_url))
        response = _client().post(es_url, data=file_content)
    except:
        logger.error('Failed to post to %s to %s due to connection issues' % (file_name, es_url))
        return False

    if response.status_code != 200:
        logger.error('Failed to post %s to %s, response returned %i' % (es_url, response.status_code))
        return False

    if response.content.decode() != 'ok':
        logger.error('Something went wrong while posting, expected "ok", got instead "%s"' % (response.content.decode()))
        return False

    return True


def _send(_type, obj, path=data_dir):
    result = _post(_type, obj, path)

    if result:
        return True

    attempts = 1
    while attempts < settings.ES_MAX_RETRIES:
        if _post(_type, obj, path):
            return True
        attempts += 1

    logger.error('Exceeded number of attempts (%i) to send data to logstash' % (settings.ES_MAX_RETRIES))
    return False


def _send_to_es(_type, objs, path=data_dir):
    logger.info('Sending to %i %s pipeline' % (len(objs), _type))
    stats = {True: {}, False: {}}
    passed = stats[True]
    failed = stats[False]
    consecutive_fails = 0
    result_before = True
    cmdline_objs = type(objs) is list

    if cmdline_objs:
        logger.info('Command line detected! Duplicates might exist for %i %s index' % (len(objs), _type))
        objs = {_id: objs[_id] for _id in range(0, len(objs))}

    for _id in objs:
        result = _send(_type, objs[_id], path)
        stats[result][_id] = objs[_id]

        # If 3 consecutive fails, Logstash is probably down
        if not result:
            consecutive_fails = consecutive_fails + 1 if result == result_before else 0

            if consecutive_fails == 3:
                logger.error('Multiple failed attempts to connect to Logstash, aborting...')
                return passed, failed
        result_before = result

        # This controls the amount of load to send logstash
        # let's try to send the same of events as logstash's LS_PIPELINE_BATCH_SIZE setting
        if (len(passed) + len(failed)) % settings.LS_PIPELINE_BATCH_SIZE == 0:
            logger.info('Wait a bit to let logstash digest queued events. Sleeping for %i seconds' % (settings.ES_LOAD_INTERVAL))
            time.sleep(settings.ES_LOAD_INTERVAL)

    # Save successfull objs and delete the ones processed correctly
    if not cmdline_objs:
        models.save(_type, passed)
        _unlink_successfull_objs(passed, path)
        
    return passed, failed
            

def feed(args):
    """
    Scan last two days worth of data from KernelCI website/storage
    and send it to an ES instance, respecting its limitations
    """
    logger.info('Feeding ES')

    if not _is_es_ok():
        return -1

    if not _is_data_dir_ok():
        return -1

    models.init()

    kci = KernelCI()

    # lavas and builds are already files downloaded to disk
    lavas = args.lavas or _download('lava', kci.get_lavas(args.how_many))
    builds = args.builds or _download('build', kci.get_builds(args.how_many))

    logger.info('Working on %i lavas and %i builds from KernelCI/command line' % (len(lavas), len(builds)))

    saved_lavas, failed_lavas = _send_to_es('lava', lavas, )
    saved_builds, failed_builds = _send_to_es('build', builds)

    models.end()

    logger.info('Lavas: sent %i to ES, %i failed' % (len(saved_lavas), len(failed_lavas.keys())))
    logger.info('Builds: sent %i to ES, %i failed' % (len(saved_builds), len(failed_builds.keys())))