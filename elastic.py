#!/usr/bin/env python3

# Takes Kernelci lavas/builds, send them to ES and save to a local sqlite
# db, data should not be duplicated in ES

import logging
import re
import time
from datetime import datetime, timedelta
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
es_host = settings.ES_HOST
es_urls = {
    'lava': settings.ES_LAVA,
    'build': settings.ES_BUILD,
    'boot': settings.ES_BOOT,
}


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
    leftovers = {'lava': {}, 'build': {}, 'boot': {}}
    for f in listdir(path):
        if f.startswith('lava_'):
            _type = 'lava'
        elif f.startswith('build_'):
            _type = 'build'
        elif f.startswith('boot_'):
            _type = 'boot'
        else:
            continue

        _id = f.replace('%s_' % (_type), '').replace('.json', '')
        leftovers[_type][_id] = f

    leftovers['lava'].update(leftovers['boot'])

    return leftovers

def _download(_type, objs, path=data_dir):

    # Get whatever lava/build previously downloaded
    # but yet not successfully posted to ES
    _load_leftovers(path)
    downloads = leftovers[_type] # [_id] = (build|lava|boot)_id.json
    logger.debug('%i %s files are already downloaded' % (len(downloads), _type))

    # Also, get a list of objects that were posted successfully
    processed = models.all_objs(_type)
 
    # When _type is 'lava', there might be boots as well
    if _type == 'lava':
        processed.update(models.all_objs('boot'))

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

    for url in es_urls.values():
        try:
            logger.debug('Pinging "%s"' % (url))
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

    es_url = es_urls[_type]

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
    lava_batch_size = 10

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

        # Controls amount of load to send logstash
        sent = len(passed) + len(failed)
        if _type == 'lava':
            if (sent % lava_batch_size) == 0:
                logger.info('Wait a bit to let logstash digest more %i events. Sleeping for %i seconds' % (10, settings.ES_LOAD_INTERVAL))
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

    # If builds or lavas are exclusively passed on command line, ignore the other one
    # otherwise it'd retrieve the regular feed_es data size (past 2 days)
    if args.builds or args.lavas or args.boots:
        builds = args.builds or {}
        lavas = args.lavas or {}
        boots = args.boots or {}
    else:
        builds = _download('build', kci.get_builds(args.how_many))
        lavas = _download('lava', kci.get_lavas(args.how_many))

        # During download, some lava files might've been switched to boot files
        # so let's just separate them and filter them out of lavas dictonary
        boots = {_id: lavas[_id] for _id in lavas.keys() if 'boot' in lavas[_id]}
        for _id in boots.keys():
            del lavas[_id]

        # Delete old objects that are no longer needed
        models.delete_old()

    logger.info('Working on %i lavas, %i builds and %i boots from KernelCI/command line' % (len(lavas), len(builds), len(boots)))

    saved_lavas, failed_lavas = _send_to_es('lava', lavas)
    saved_builds, failed_builds = _send_to_es('build', builds)
    saved_boots, failed_boots = _send_to_es('boot', boots)

    models.end()

    logger.info('Lavas: sent %i to ES, %i failed' % (len(saved_lavas), len(failed_lavas.keys())))
    logger.info('Builds: sent %i to ES, %i failed' % (len(saved_builds), len(failed_builds.keys())))
    logger.info('Boots: sent %i to ES, %i failed' % (len(saved_boots), len(failed_boots.keys())))


def setup(args):
    """
    Set up elasticsearch by putting mappings templates
    thus allowing aliasing and other first-time settings to
    be made
    """

    logger.info('Setting up ElasticSearch')

    headers = {'Content-Type': 'application/json'}

    # Get mappings files
    for file_name in listdir('mapping_templates'):
        with open('mapping_templates/%s' % (file_name)) as fh:
            mapping = fh.read()

        logger.info('Setting "%s" mapping' % (file_name))
        mapping_name = file_name.replace('.json', '')
        url = '%s/_template/%s' % (es_host, mapping_name)

        try:
            res = _client().put(url, headers=headers, data=mapping)
        except:
            logger.error('Failed to send "%s" to ElasticSearch due to connection issues' % (file_name))
            continue

        if res.status_code != 200:
            logger.error('Failed to send "%s" to ElasticSearch, it returned something different than 200' % (file_name))
            logger.error(res.content.decode())
            continue

        logger.info('ES answered: %s' % (res.content.decode()))


def drp(args):
    logger.info('Data Rentention Ploicy will clean up indices older than %i days in ElasticSearch' % (args.drp_days))

    # Get drp date, i.e., YYYY MM DD
    days = args.drp_days
    drp_datetime = datetime.now() if days == 0 else datetime.now() - timedelta(days=days)
    drp_date = drp_datetime.date()

    # Get available indices from ElasticSearch
    logger.info('Retrieving list of indices')
    url = '%s/_cat/indices' % (es_host)
    try:
        res = _client().get(url)
    except:
        logger.error('Failed to retrieve list of indices due to conectivity issues')
        return -1

    if res.status_code != 200:
        logger.error('Failed to retrieve list of indices from ElasticSearch, it returned something different than 200')
        logger.error(res.content.decode())
        return -1

    # Get target indices
    content = res.content.decode()
    indices = re.findall(r'\s((?:log|test|boot|build)-\d{4}\.\d{2}\.\d{2})\s', content)

    to_delete = []
    for index in indices:
        index_date = datetime.strptime(index.split('-')[1], '%Y.%m.%d').date()
        if drp_date > index_date:
            to_delete.append(index)

    # Delete all
    if len(to_delete) == 0:
        logger.info('No indices to delete')
        return 0

    url = '%s/%s' % (es_host, ','.join(to_delete))
    try:
        res = _client().delete(url)
    except:
        logger.error('Failed to delete indices due to conectivity issues')
        return -1

    if res.status_code != 200:
        logger.error('Failed delete indices from ElasticSearch, it returned something different than 200')
        logger.error(res.content.decode())
        return -1

    logger.info('Deleted indices %s' % (to_delete))
    return 0
