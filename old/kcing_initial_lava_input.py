"""

This script will go to lkft.validation.linaro.org and grab all test jobs
that are complete, from kernelci, using kernel v4.20 and booted to qemu.

The same can be queried through: https://lkft.validation.linaro.org/results/query/+custom?entity=testjob&conditions=testjob__health__exact__Complete,submitter__exact__kernel-ci,description__contains__v4.20,actual_device_id__contains__qemu

Today (Dec 14th, 2018) this returns 100+ test jobs

Then, for each test job this script will:
 - download test job's definition
 - from definition:
  - grep `metadata[image.url]`, which will return the location in storage.kernelci.org
    containing `build.json` and all test job runs separated by labs 
  - submit build.json to https://ochaws.com/build and save it locally to make sure
    no to have duplicates
   - this will create a new document in ES in /build index
  - replace `api.kernelci.org/callback/lava` with `ochaws.com` in `notify[callback][url]`
  - submit a test job with new definition, just checking beforehand if:
   - `actions[deploy][images][kernel][url]` and `actions[deploy][images][ramdisk][url]` exist
  - replacing definition urls will implicate that when lava is done with the test job
    https://ochaws.com/boot will be invoked with test job's results
   - with results coming in, logstash will split that into /definition, /log, /result, and
     /boot indices
 - done

"""

import xmlrpc.client
import yaml
import requests
import time
from pprint import pprint

ES_HOST = 'https://ochaws.com'
KCI_CALLBACK = 'https://api.kernelci.org/callback/lava'
USER = 'charles.oliveira'
TOKEN = open('lkft.validation.linaro.org.token', 'r').read()
HOST = 'lkft.validation.linaro.org'
QUERY = 'testjob__health__exact__Complete,submitter__exact__kernel-ci,description__contains__v4.20,actual_device_id__contains__qemu'
CHAWS_TOKEN_NAME = 'chaws-lkft-token'
KCI_TOKEN_NAME = 'kernel-ci-callback'
TIMEOUT = 3


def does_resource_exist(resource_url):
    if resource_url is None:
        return False

    r = requests.head(resource_url)
    return r.status_code is 200


def submit_testjob(rpc_server, definition):
    print('Sleeping for %i seconds before submiting a new test job' % (TIMEOUT))
    time.sleep(TIMEOUT)
    return rpc_server.scheduler.jobs.submit(definition)


def submit_build(build_url):
    # Get build.json contents
    res = requests.get(build_url)
    if res.status_code is not 200:
        print('Build "%s" not found! Cannot continue...')
        return False

    # Send it to ES instance
    build_contents = res.content.decode('utf-8')
    res = requests.post('/'.join([ES_HOST, 'build']), data = build_contents)
    return res.status_code is 200


def process_definition(definition_str):
    try:
        definition = yaml.load(definition_str)
    except:
        print('Failed to parse definition')
        return False

    actions = definition['actions']
    image_url = None
    ramdisk_url = None
    for action in actions:
        if 'deploy' in action:
            imgs = action['deploy']['images']
            image_url = imgs['kernel']['url']
            ramdisk_url = imgs['ramdisk']['url']

    if not does_resource_exist(image_url):
        print('Kernel image "%s" no longe exists! Quitting test job...')
        return False

    if not does_resource_exist(ramdisk_url):
        print('Ramdisk image "%s" no longe exists! Quitting test job...')
        return False

    # Kernelci keeps all significant files within
    # /tree/branch/git-describe/arch/config, which we're calling here build_url
    build_url = definition['metadata']['image.url'] + 'build.json'
    if not does_resource_exist(build_url):
        print('Build "%s" no longer exists! Quitting test job...')
        return False
    
    # Send build to ES
    if not submit_build(build_url):
        print('Failed to send build.js to ES! Quitting test job')
        return False

    return True

    
def process_testjob(rpc_server, testjob):
    # check if there's an id
    if not testjob['id'] > 0:
        return
    
    print('Processing test job %i' % (testjob['id']))

    definition = testjob['definition']
    if not process_definition(definition):
        print('Could not continue test job because its definition is faulty!')
        return

    # Replaces kernelci url with ES'
    if KCI_CALLBACK not in definition:
        print('This test job contains a definition that did not send a callback notification')
        return

    new_definition = definition.replace(KCI_CALLBACK, ES_HOST)
    new_definition = new_definition.replace(KCI_TOKEN_NAME, CHAWS_TOKEN_NAME)
    new_testjob_id = submit_testjob(rpc_server, new_definition)
    return new_testjob_id


def main():
    # Start up RPC connection
    rpc_server = xmlrpc.client.ServerProxy("https://%s:%s@%s/RPC2" % (USER, TOKEN, HOST), allow_none=True)

    # Run custom query
    result = rpc_server.results.make_custom_query("testjob", QUERY)
    print('Found %i test jobs from kernelci at %s for kernel v4.20 complete jobs submitted to qemu devices' % (len(result), HOST))
    for testjob in result:
        new_testjob_id = process_testjob(rpc_server, testjob)
        print('Test job processed and another test job has been submitted to %s with id %i' % (HOST, new_testjob_id))

main()
