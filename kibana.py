#!/usr/bin/env python3

import logging
import requests
import json


import settings


logger = logging.getLogger()

kibana_filename = 'kcing.kibana'
kibana_mapping = 'mapping_templates/kibana.json'
es_host = settings.ES_HOST
headers = {'Content-Type': 'application/json'}


def backup(args):
    logger.info('Backing up kibana data & mapping')

    mapping_url = '%s/.kibana_1/_mapping' % (es_host)
    data_url = '%s/.kibana_1/_search' % (es_host)
    search = """{
       "size": 10000,
        "query": {
            "match_all": {}
        }
    }"""

    try:
        data_res = requests.post(data_url, headers=headers, data=search)
        mapping_res = requests.get(mapping_url, headers=headers)
    except:
        logger.error('Failed to backup kibana due to connection issues')
        return

    if data_res.status_code != 200:
        logger.error('Failed to backup kibana data due to http return code %i' % (data_res.status_code))
        logger.error('%s' % (data_res.content.decode()))
        return

    if mapping_res.status_code != 200:
        logger.error('Failed to backup kibana mappings due to http return code %i' % (mapping_res.status_code))
        logger.error('%s' % (mapping_res.content.decode()))
        return

    # Save data to kcing.kibana
    objects = json.loads(data_res.content.decode())['hits']['hits']
    with open(kibana_filename, 'w') as fh:
        json.dump(objects, fh, sort_keys = True, indent = 2)
    logger.info('Kibana objects saved to %s' % (kibana_filename))

    # Save mapings to mapping_templates/kibana.json
    mapping = json.loads(mapping_res.content.decode())['.kibana_1']
    mapping['index_patterns'] = ['.kibana_1']
    mapping['settings'] = {'number_of_shards': 1}
    with open(kibana_mapping, 'w') as fh:
        json.dump(mapping, fh, sort_keys = True, indent = 2)
    logger.info('Kibana mappings saved to %s' % (kibana_mapping))


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
            url = '%s/.kibana_1/_doc/%s' % (es_host, o['_id'])
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

        logger.info('%s: %s' % (o['_id'], res.content.decode()))
        sent = sent + 1

    logger.info('Sent %i saved objects to kibana, and %i failed' % (sent, failed))
