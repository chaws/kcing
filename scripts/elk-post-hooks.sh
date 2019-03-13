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
    echo "kcing is waiting kibana to be ready ($attempts/60)"
done

# Exit if kibana didn't start correctly
if [ $attempts == 60 ]
then
    exit $attempts
fi

# Make sure to always start the container with the latest kibana objects
cd /opt/kcing
./kcing.py setup_kbn

# Feed initial data
if [ ! -e /var/lib/elasticsearch/first_time ]
then
    # Make sure it won't run next time a container starts
    touch /var/lib/elasticsearch/first_time

    # Set elasticsearch mappings
    ./kcing.py setup_es

    chmod +x ./scripts/wait_logstash.sh
    ./scripts/wait_logstash.sh

    echo "First time only: feeding ElasticSearch with 2500-ish objects. Go grab a cup of coffee..."
    $(./kcing.py feed_es --how-many 500 || exit 0)
fi
