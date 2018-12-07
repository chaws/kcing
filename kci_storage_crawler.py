import urllib.request
from urllib.parse import urlparse
import re
import sys
import os
import json
import datetime

# KernelCI storage site
KCI_STORAGE_SITE = "https://storage.kernelci.org"

# urls are like this
# /tree/branch/tag/arch/config/lab
# then everything for that build and its tests will be inside

# Regex for a.href
a_href_regex = re.compile('a href="(\w.*?)/"')
a_href_regex_include_files = re.compile('a href="(\w.*?)"')

# Regex to find lab name on a url ending
lab_regex = re.compile('.*lab-\w+$')

# Regex to find if file is a lava result in json
lava_result_file_regex = re.compile('.*lava-json-.*?\.json$')

# Regex to filter tags for v4.20 of kernel only (narrowing down results)
v4_20_regex = re.compile('.*v4\.20-.*')

# Files to keep trees, branches, tags, archs, confs, labs, builds and results
files = {}
for f in ['trees', 'branches', 'tags', 'archs', 'configs', 'labs', 'builds', 'results']:
    files[f] = open(f, 'a+')

run_once = False
if len(sys.argv) == 2:
    run_once = True

# Given an url, return all hrefs
def fetch(url, include_files = False):
    url = url.rstrip()
    log("Fetching '%s'... " % (url))
    content = urllib.request.urlopen(url).read()

    regex = a_href_regex_include_files if include_files else a_href_regex
    hrefs = regex.findall(str(content))

    log("got '%i' results" % (len(hrefs)))
    return ['%s/%s' % (url, href) for href in hrefs]

# Given an url, download it
def download(url):
    url = url.rstrip()
    log("Downloading %s... " % (url))
    content = urllib.request.urlopen(url).read()
    log("done")

    parsed_url = urlparse(url)
    path = parsed_url.path

    # Remove unwanted chars from path
    path = path.replace('=', '_')
    path = path.replace('+', '_')
    path = path.replace(' ', '_')
    path = path.strip('/')

    dirname = os.path.dirname(path).strip('/')
    filename = os.path.basename(path).strip('/')

    log("Making sure '%s' exists..." % (dirname))
    os.makedirs(dirname, exist_ok = True)
    log("done")

    # We could be saving only a directory
    if path != '':
        log("Saving '%s' to '%s'... " % (filename, dirname))
        with open(path, 'w') as fd:
            fd.write(str(content))
        log("done")

# We're sacrificing speed in exchange for space
# since some
def append_to_file(filename, item):
    f = files[filename]
    if type(item) == list:
        for i in item:
            f.write('%s\n' % i)
    else:
        f.write('%s\n' % item)

def close_file(filename):
    files[filename].flush()
    files[filename].close()
    
    # In case we run this script multiple times, remove 
    # duplicate entries
    os.system("perl -i -ne 'print if ! $x{$_}++' %s" % (filename))

log_file = open('kci_storage_crawler.log', 'w')
def log(message):
    log_file.write(str(datetime.datetime.now()))
    log_file.write(': %s\n' % (message))
    log_file.flush()
    
log("***** Crawling %s ******" % (KCI_STORAGE_SITE))
    
# Get trees
# trees = fetch(KCI_STORAGE_SITE)
trees = ['https://storage.kernelci.org/mainline']
append_to_file('trees', trees)
del trees

# Close trees file so it can be safely used to retrieve branches
close_file('trees')

# From each tree, get its branches
log("Fetching branches")
with open('trees', 'r') as trees:
    for tree in trees:
        branches = fetch(tree)
        append_to_file('branches', branches)

        if run_once:
            break

# Close branches file so it can be safely used to retrieve tags
close_file('branches')

# From each branch, get its tags
log("Fetching tags")
with open('branches', 'r') as branches:
    for branch in branches:
        tags = fetch(branch)
        append_to_file('tags', tags)

        if run_once:
            break

# Close tags file so it can be safely used to retrieve archs
close_file('tags')

# From each tag, get its architectures
log("Fetching archs")
with open('tags', 'r') as tags:
    for tag in tags:
        if v4_20_regex.match(tag):
            archs = fetch(tag)
            append_to_file('archs', archs)

        if run_once:
            break

# Close archs file so it can be safely used to retrieve configs
close_file('archs')

# From each architecture, get its config
log("Fetching configs")
with open('archs', 'r') as archs:
    for arch in archs:
        configs = fetch(arch)
        append_to_file('configs', configs)

        if run_once:
            break

# Close configs file so it can be safely used to retrieve labs and builds
close_file('configs')

# From within each config, get build.json and its lab where it ran on
log("Fetching builds and labs")
with open('configs', 'r') as configs:
    for config in configs:
        items = fetch(config, include_files=True)

        # Search for labs of build files
        for item in items:
            # Get build.json files
            if item.endswith('build.json'):
                append_to_file('builds', item)

                # Also download the file so we can insert it to logstash later on
                download(item)

            # Get all labs
            elif lab_regex.match(item):
                append_to_file('labs', item)

# Close builds and labs file so it can be safely used to retrieve results from labs
close_file('builds')
close_file('labs')

sys.exit()
# From each lab, finally get results of the type 'lava-json-*.json'
with open('labs', 'r') as labs:
    for lab in labs:
        items = fetch(lab)
        for item in items:
            if lava_result_file_regex.match(item):
                append_to_file('results', item)
                download(item)

            if run_once:
                break

close_file('results')

log("Done crawling, zzzZZZZ")
