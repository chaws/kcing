#!/bin/bash

attempts=0
while [ $attempts != 60 ]
do 
    res=`curl -s localhost:8337 -o -` 
    if [ "$res" == "ok" ]
    then 
        attempts=0
        break
    fi
    sleep 2
    ((attempts++))
    echo "kcing is waiting for logstash ($attempts/60)"
done
exit $attempts
