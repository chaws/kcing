#!/bin/bash

# Make sure to always start the container with up-to-date kibana objects and mappings and logstash pipeline
cd /opt/kcing
git pull origin master
