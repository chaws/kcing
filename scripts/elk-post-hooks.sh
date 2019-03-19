#!/bin/bash

# Feed initial data
if [ ! -e /var/lib/elasticsearch/first_time ]
then
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

    # Make sure it won't run next time a container starts
    touch /var/lib/elasticsearch/first_time

    cd /opt/kcing

    # Set elasticsearch mappings
    ./kcing.py setup_es

    # Restore 
    ./kcing.py setup_kbn
fi
