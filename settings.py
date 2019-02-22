# Settings file for KCING

from os import getenv
from os.path import dirname, join, isfile

local = {}
if isfile('local_settings.py'):
    from local_settings import settings
    local = settings

def env_or_local(var_name, default=None):
    return getenv(var_name) or local.get(var_name) or default

# Main kernelci domain name
KCI_HOST   = env_or_local('KCI_HOST', 'kernelci')
KCI_SCHEME = env_or_local('KCI_SCHEME', 'https')

# ES links, it's actually logstash listening to those handlers
ES_BOOT  = env_or_local('ES_BOOT')
ES_BUILD = env_or_local('ES_BUILD')

# If an attempt to send data to ES fails, retry for ES_MAX_RETRIES before giving up
ES_MAX_RETRIES = env_or_local('ES_MAX_RETRIES', 3)

# Number of seconds to sleep after every LS_PIPELINE_BATCH_SIZE objects are sent to ES, thus reducing load on logstash
ES_LOAD_INTERVAL = env_or_local('ES_LOAD_INTERVAL', 5)

# Logstash settings
# Home folder of logstash
LS_HOME                 = env_or_local('LS_HOME')

# Queueing type: persisted (disk) or memory (ram)
LS_QUEUE_TYPE           = env_or_local('LS_QUEUE_TYPE', 'persisted')

# Pipeline configuration file path, defaults to kcing repo
LS_PATH_CONFIG          = env_or_local('LS_PATH_CONFIG', join(dirname(__file__), "kcing_pipeline.conf"))

# Number of events logstash will handle in the 'input' section before going to 'filters'
LS_QUEUE_MAX_EVENTS     = env_or_local('LS_QUEUE_MAX_EVENTS', 200)
LS_PIPELINE_BATCH_SIZE  = env_or_local('LS_PIPELINE_BATCH_SIZE', 100)

# Database to store progress of processed boots/builds
KCING_DB = env_or_local('KCING_DB', 'kcing.db')

# Number of days to keep data, 3 is a good number since we're always fetching
# last 2 days worth of data
DRP_DAYS = env_or_local('DRP_DAYS', 3)
