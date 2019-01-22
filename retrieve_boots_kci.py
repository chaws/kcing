import time
import requests
import os
import re
import json

RUN_ONCE = True

ES_HOST = 'https://ochaws.com'
ES_BOOT = os.path.join(ES_HOST, 'boot')
ES_BUILD = os.path.join(ES_HOST, 'build')

KCI_URL = 'https://kernelci.org'
STORAGE_KCI_URL = 'https://storage.kernelci.org'
BOOTS_PAGE = os.path.join(KCI_URL, 'boot')
AJAX_BOOT = os.path.join(KCI_URL, '_ajax', 'boot')
QUERY_STRING = AJAX_BOOT + '?date_range=14&sort=created_on&sort_order=1&limit=%s&skip=%s&fields=arch&fields=defconfig_full&fields=git_branch&fields=job&fields=kernel&fields=lab_name'

log_file = open('retrieve_boots_kci.log', 'w')

def log(msg):
    timing = time.strftime("%Y-%m-%d %H:%M:%S")
    log_file.write('[%s] %s \n' % (timing, msg))
    log_file.flush()

# Used to submit boot or build
def submit_to_es(es, resource_url):
    if not does_resource_exist(resource_url):
        log('"%s" does not exist!')
        return False

    # Get resource contents
    log('Downloading %s' % resource_url)
    res = requests.get(resource_url)
    if res.status_code is not 200:
        log('Resource "%s" not found! Cannot continue...' % resource_url)
        return False

    # Send it to ES instance
    log('Posting to %s' % es)
    resource_contents = res.content.decode('utf-8')
    res = requests.post(es, data = resource_contents)
    ans = res.status_code is 200
    if not ans:
        log('failed!')

    return ans

def does_resource_exist(resource_url):
    if resource_url is None:
        return False

    r = requests.head(resource_url)
    return r.status_code is 200

def base_path(boot):
    return os.path.join(STORAGE_KCI_URL, boot['job'], boot['git_branch'], boot['kernel'], boot['arch'], boot['defconfig'])

# First request to keep meaningful headers and csrf
log('Requesting %s' % (BOOTS_PAGE))
client = requests.session()
r = client.get(BOOTS_PAGE)

# Get csrf
m = re.search('csrf-token.*?content="([^"]+)"', str(r.content))
csrf_token = m.groups(1)[0]
client.headers['x-csrftoken'] = csrf_token
log(client.headers)

limit = 1000
builds = set()
for skip in range(0, 35000, limit):

    query = QUERY_STRING % (limit, skip)
    log('Requesting %s' % (query))

    try:
        r = client.get(query)
        response = json.loads(r.content.decode())
        for boot in response['result']:

            # Get boot file and send it to ES
            boot_file = 'lava-json-%s.json' % (boot['board'])
            boot_file_url = os.path.join(base_path(boot), boot['lab_name'], boot_file)
            submit_to_es(ES_BOOT, boot_file_url)           
 
            build_file_url = os.path.join(base_path(boot), 'build.json')
            if build_file_url not in builds:
                if submit_to_es(ES_BUILD, build_file_url):
                    builds.add(build_file_url)
            
            if RUN_ONCE:
                break
                
    except:
        log('Could not dowload something, lets sleep for 5 secs')
        time.sleep(5)
        log('moving on')

    if RUN_ONCE:
        break

log_file.close()
