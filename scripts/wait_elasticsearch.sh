#!/bin/bash

attempts=0
while [ $attempts != 60 ]
do 
    curl -s localhost:9200 -o - > /dev/null
    if [ "$?" == "0" ]
    then 
        attempts=0
        break
    fi
    sleep 2
    ((attempts=$attempts + 1))
done
exit $attempts
