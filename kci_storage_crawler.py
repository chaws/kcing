import urllib.request
from urllib.parse import urlparse
import re
import sys
import os
import json

KCI_STORAGE_SITE = "https://storage.kernelci.org"

# urls are like this
# /tree/branch/tag/arch/config/lab
# then everything for that build and its tests will be inside

# Regex for a.href
a_href_regex = re.compile('a href="(\w.*?)/"')
a_href_regex_include_files = re.compile('a href="(\w.*?)"')

# Regex to find lab name on a url ending
lab_regex = re.compile('lab-\w+$')

# Regex to find if file is a lava result in json
lava_result_file_regex = re.compile('lava-json-.*?\.json')

# Given an url, return all hrefs
def fetch(url, include_files = False):
    sys.stderr.write("Fetching '%s'... " % (url))
    content = urllib.request.urlopen(url).read()

    regex = a_href_regex if include_files else a_href_regex_include_files
    hrefs = regex.findall(str(content))

    sys.stderr.write("got '%i' results\n" % (len(hrefs)))
    return ['%s/%s' % (url, href) for href in hrefs]

# Save list to file as json
def to_file(name, l):
    obj = {name: l}
    sys.stderr.write("Saving %s to %s.json (%i objects)... " % (name, name, len(l)))
    with open('%s.json' % (name), 'w') as json_file:
        json.dump(obj, json_file)
        json_file.flush()
    sys.stderr.write(" done\n")

# Given an url, download it
def download(url):
    sys.stderr.write("Downloading %s... " % (url))
    content = urllib.request.urlopen(url).read()
    sys.stderr.write(" done")

    parsed_url = urlparse(url)
    path = parsed_url.path

    # Remove unwanted chars from path
    path = path.replace('=', '_')
    path = path.replace('+', '_')

    dirname = os.path.dirname(path)
    filename = os.path.basename(path)

    sys.stderr.write("Saving %s to %s... " % (filename, dirname))
    os.makedirs(dirname, exist_ok = True)
    with open(path, 'w') as fd:
        fd.write(content)
        fd.flush()
    sys.stderr.write("done")

sys.stderr.write("***** Crawling %s ******\n\n" % (KCI_STORAGE_SITE))
    
# Get trees
trees = fetch(KCI_STORAGE_SITE)
to_file('trees', trees)

# From each tree, get its branches
branches = []
for tree in trees:
    branches += fetch(tree)

del trees
to_file('branches', branches)

# From each branch, get its tags
tags = []
for branch in branches:
    tags += fetch(branch)

del branches
to_file('tags', tags)

# From each tag, get its architectures
archs = []
for tag in tags:
    archs += fetch(tag)

del tags
to_file('archs', archs)

# From each architecture, get its config
configs = []
for arch in archs:
    configs += fetch(arch)

del archs
to_file('configs', configs)

# From within each config, get build.json and its lab where it ran on
builds = []
labs = []
for config in configs:
    items = fetch(arch, include_files=True)

    # Search for labs of build files
    for item in items:
        # Get build.json files
        if item.endswith('build.json'):
            builds.append(items)

        # Get all labs
        elif lab_regex.match(item):
            labs.append(item)

del configs
to_file('builds', builds)
to_file('labs', labs)

# From each lab, finally get results of the type 'lava-json-*.json'
results = []
for lab in labs:
    items = fetch(lab)
    for item in items:
        if lava_result_file_regex.match(item):
            results.append(item)

del labs
to_file('results', results)

# Now that everything is saved to its own files
# let's download build.json and lava-json-*.json files
for build in builds:
    download(build)

for result in results:
    download(result)
