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
KCI_HOST   = env_or_local('KCI_HOST', 'kernelci.org')
KCI_SCHEME = env_or_local('KCI_SCHEME', 'https')
KCI_NON_LAVA_LAB = env_or_local('KCI_NON_LAVA_LAB', 'lab-baylibre-seattle')

# ES links, it's actually logstash listening to those handlers
ES_HOST  = env_or_local('ES_HOST', 'http://localhost:9200')
ES_LAVA  = env_or_local('ES_LAVA', 'http://localhost:8338')
ES_BUILD = env_or_local('ES_BUILD', 'http://localhost:8337')
ES_BOOT  = env_or_local('ES_BOOT', 'http://localhost:8007')

# If an attempt to send data to ES fails, retry for ES_MAX_RETRIES before giving up
ES_MAX_RETRIES = env_or_local('ES_MAX_RETRIES', 3)

# Number of seconds to sleep after every LS_PIPELINE_BATCH_SIZE objects are sent to ES, thus reducing load on logstash
ES_LOAD_INTERVAL = env_or_local('ES_LOAD_INTERVAL', 3)

# Logstash settings
# Home folder of logstash
LS_HOME                 = env_or_local('LS_HOME')

# Queueing type: persisted (disk) or memory (ram)
LS_QUEUE_TYPE           = env_or_local('LS_QUEUE_TYPE', 'persisted')

# Pipeline configuration file path, defaults to kcing repo
LS_PATH_CONFIG          = env_or_local('LS_PATH_CONFIG', join(dirname(__file__), "kcing_pipeline.conf"))

# Number of documents each worker will handle at a time
LS_PIPELINE_BATCH_SIZE  = env_or_local('LS_PIPELINE_BATCH_SIZE', 1)

# Number of workers logstash will span to parallel process events
LS_NUM_WORKERS = env_or_local('LS_NUM_WORKERS', 1)

# Database to store progress of processed lavas/builds
KCING_DB = env_or_local('KCING_DB', 'kcing.db')

# Number of days to keep data in ES and kcing.db
DRP_DAYS = env_or_local('DRP_DAYS', 4)
