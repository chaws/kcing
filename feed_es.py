#!/usr/bin/env python3

import logging


logger = logging.getLogger()


class FeedEs(object):
    """
    Takes Kernelci boots/builds, send them to ES and save to a local sqlite
    db, data should be be duplicated in ES
    """

    def feed(self):
        """
        Scan last two days worth of data from KernelCI website/storage
        and send it to an ES instance, respecting its limitations
        """
        logger.info('Feeding ES with KernelCI data')
