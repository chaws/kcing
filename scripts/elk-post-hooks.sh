#!/bin/bash

# Make sure kibana is ready (running isn't enough)
# https://github.com/elastic/kibana/issues/25464
attempts=0
while [ $attempts != 60 ]
do 
    ack=$(curl -s -X GET localhost:5601 -o - || echo 'Kibana server is not ready yet')
    if [ "$ack" != "Kibana server is not ready yet" ]
    then
        break
    fi
    sleep 2
    ((attempts++))
done

# Exit if kibana didn't start correctly
if [ $attempts == 60 ]
then
    exit $attempts
fi

# Make sure to always start the container with the latest kibana objects
cd /opt/kcing && ./kcing.py setup_kbn
