#!/usr/bin/env python3

#This new script should keep track of which builds and boots were already processed
#
#1. Add exception handling when CSRF has expired
#2. Save builds/boots ids into a db
#2.1. this will prevent adding duplicates
#3. Save a list of builds/boots that failed to download
#3.1. Attempt downloading max of 5 times

import json
import logging
import os
import re
import requests
import time
import sys

from urllib.parse import urlencode

#import models
import settings

logger = logging.getLogger()

class CannotContinue(Exception):
    """We can't really do anything for now"""
    pass

class KernelCI(object):

    def __init__(self, max_retries=5, max_per_req=1000):
        # Browser-like client
        self.client = requests.session()
        self.client.headers['Connection'] = 'keep-alive'

        self.boots = []
        self.builds = []

        # Urls
        self.url_scheme = settings.KCI_SCHEME + '://'
        self.url = settings.KCI_HOST
        self.storage_url = self.url_scheme + 'storage.%s' % (self.url)
        self.url = self.url_scheme + self.url
        self.boot_url = os.path.join(self.url, '_ajax', 'boot')
        self.build_url = os.path.join(self.url, '_ajax', 'build')

        # Csrf regex (extract from meta tag)
        self.csrf_regex = re.compile('csrf-token.*?content="([^"]+)"', re.S)

        # Max client retries before giving up
        self.max_retries = max_retries

        # Max number of objects to retrieve per request to kernelci
        self.max_objs_per_request = max_per_req

    def _http(self, url, method='get', blocking=True):
        if method not in ['get', 'head']:
            logger.error('Http method "%s" is unknown' % (method))

            if blocking:
                raise CannotContinue('Http method "%s" is unknown' % (method))

            return

        attempts = 0
        wait_for = 2
        client_method = getattr(self.client, method)
        method = method.upper()
        while attempts < self.max_retries:
            try:
                logger.debug('%s "%s"' % (method, url))
                response = client_method(url)
                return response
            except:
                logger.warning('Failed to %s "%s", trying again in %i seconds' % (method, url, wait_for))
                time.sleep(wait_for)
                attempts += 1
                wait_for *= 2

        if blocking:
            raise CannotContinue('Exceeded attempts to %s "%s"' % (method, url))

    def _refresh_csrf_token(self):
        response = self._http(self.url) 
        html = response.content.decode()
        matches = self.csrf_regex.search(html)
        if matches:
            token = matches.groups(1)[0]
            self.client.headers['x-csrftoken'] = token 
            logger.info('New csrf "%s"' % (token))
            return token
        else:
            raise CannotContinue('Failed to retrieve new csrf token')

    def _get_docs(self, _type, date_range=2, how_many=-1):
        docs = []
        url = None
        limit = self.max_objs_per_request

        if _type == 'boot':
            url = self.boot_url
        elif _type == 'build':
            url = self.build_url
        else:
            logger.error('Unknown doc_type "%s"' % (_type))
            return

        if how_many > 0 and how_many < limit:
            limit = how_many
        
        params = {
            'date_range': date_range,
            'skip': 0,
            'limit': limit,
            'sort': 'created_on',
            'sort_order': 1,
        }

        count = 1
        attempts = 0
        self._refresh_csrf_token()
        while count > 0 and attempts <= self.max_retries:
            query = urlencode(params)
            response = self._http(url + '?' + query)
            if response.status_code != 200:
                attempts += 1
                logger.debug('Failed to retrieve %s, attempt (%i) to refresh csrf' % (doc_type, attempts))
                self._refresh_csrf_token()
                continue

            result = json.loads(response.content.decode())
            objects = result['result']

            count = len(objects)
            logger.debug('Retrieved %i docs' % (count))
            if count:
                docs += objects

            if how_many > 0 and len(docs) >= how_many:
                break

            # Skip `count` objects on next request
            params['skip'] += count

            # Reset attempts
            attempts = 0

        return docs

    def _docs_to_links(self, _type, how_many=-1):
        """Get a list of retrieved doc_types, links are ready to download from storage"""
        logger.info('Retrieving %ss from KernelCI' % (_type))
        docs = self._get_docs(_type, how_many=how_many)
        ready_to_download = {}

        for d in docs:
            _id = d['_id']['$oid']
            path = d['file_server_resource']

            filename = ''
            if _type == 'boot':
                lab = d['lab_name']
                filename = os.path.join(lab, 'lava-json-%s.json' % (d['board']))
            elif _type == 'build':
                filename = 'build.json'
            else:
                raise CannotContinue('Unexpected doc_type "%s"' % (_type))

            ready_to_download[_id] = os.path.join(self.storage_url, path, filename)

        logger.info('Got %i' % (len(ready_to_download)))
        return ready_to_download

    def get_boots(self, how_many=-1):
        return self._docs_to_links('boot', how_many=how_many)

    def get_builds(self, how_many=-1):
        return self._docs_to_links('build', how_many=how_many)
