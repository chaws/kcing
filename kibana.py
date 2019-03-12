#!/usr/bin/env python3

import logging
import requests
import json


import settings


logger = logging.getLogger()

kibana_filename = 'kcing.kibana' 
es_host = settings.ES_HOST
headers = {'Content-Type': 'application/json'}


def backup(args):
    logger.info('Backing up kibana')

    url = '%s/.kibana_1/_search' % (es_host)
    search = """{
       "size": 10000,
        "query": {
            "match_all": {}
        }
    }"""

    try:
        res = requests.post(url, headers=headers, data=search)
    except:
        logger.error('Failed to backup kibana due to connection issues')
        return

    if res.status_code != 200:
        logger.error('Failed to backup kibana due to http return code %i' % (res.status_code))
        logger.error('%s' % (res.content.decode()))
        return

    objects = json.loads(res.content.decode())['hits']['hits']
    with open(kibana_filename, 'w') as fh:
        json.dump(objects, fh, sort_keys = True, indent = 2)


def setup(args):
    logger.info('Setting up kibana dashboards/visualizations/index-patterns/searches')
    
    objects = None
    with open(kibana_filename, 'r') as fh:
        objects = json.load(fh)

    if objects == None or len(objects) == 0:
        logger.error('Failed to read %s or it is empty' % (kibana_filename))
        return

    sent = 0
    failed = 0
    for o in objects:
        try:
            url = '%s/.kibana_1/doc/%s' % (es_host, o['_id'])
            data = json.dumps(o['_source'])
            res = requests.put(url, headers=headers, data=data)
        except:
            logger.error('Failed to restore %s in kibana index' % (o['_id']))
            failed = failed + 1
            continue

        if res.status_code != 200 and res.status_code != 201:
            logger.error('Failed to restore %s due to kibanas http return %i' % (o['_id'], res.status_code))
            logger.error(res.content.decode())
            failed = failed + 1
            continue

        sent = sent + 1

    logger.info('Sent %i saved objects to kibana, and %i failed' % (sent, failed))
