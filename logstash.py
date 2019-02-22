#!/usr/bin/env python3

import logging

from os.path import isdir, isfile

import settings

logger = logging.getLogger()


# Make sure the following settings are enabled
# - pipeline.id: kcing
#   path.config: "/path/to/kcing_pipeline.conf"
#   pipeline.batch.size: 100
#   queue.type: persisted
#   queue.max_events: 200
def _apply_setup(content):
    config = {
        'queue_type': settings.LS_QUEUE_TYPE,
        'max_events': settings.LS_QUEUE_MAX_EVENTS,
        'batch_size': settings.LS_PIPELINE_BATCH_SIZE,
        'path_config': settings.LS_PATH_CONFIG,
    }

    if not isfile(config['path_config']):
        logger.error('Pipeline config is not a file or do not exist "%s"' % (config['path_config']))
        return

    if config['queue_type'] not in ['memory', 'persisted']:
        logger.error('Queue type "%s" should be memory or persisted' % (queue_type))
        return

    # Too lazy to find/replace original config content FIXME
    new_config = """
- pipeline.id: kcing
  path.config: "%(path_config)s"
  pipeline.batch.size: %(batch_size)i
  queue.type: %(queue_type)s
  queue.max_events: %(max_events)i
"""
    return new_config % config

def setup(args):
    logger.info('Setting up Logstash')

    ls_home = settings.LS_HOME
    if ls_home is None or not isdir(ls_home):
        logger.error('Logstash home is not set or is not a directory! Please provide correct location using LS_HOME as env var or local_settings.py')
        return -1

    config_filename = '%s/config/pipelines.yml' % (ls_home)
    if not isfile(config_filename):
        logger.error('Logstash config file "%s" was not located' % (config_filename))
        return -1

    with open(config_filename, 'r') as file_handler:
        config_content = file_handler.read()

    # Change
    config_updated = _apply_setup(config_content)
    if config_updated is None:
        return -1 # something is wrong

    logger.info('New configuration for Logstash')
    logger.info(config_updated)

    with open(config_filename, 'w') as file_handler:
        file_handler.write(config_updated)

    return 0 
