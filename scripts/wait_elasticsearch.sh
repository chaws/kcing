#!/bin/bash

PORT=${PORT:-9200}
attempts=0
while [ $attempts != 60 ]
do 
    ack=$(curl -s -X POST localhost:$PORT/dummy -o - || echo down)
    if [[ "$ack" =~ .*dummy.* ]]
    then
        curl -s -X DELETE localhost:$PORT/dummy -o - > /dev/null
        attempts=0
        break
    fi
    sleep 2
    ((attempts++))
done
exit $attempts
