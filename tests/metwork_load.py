#!/bin/bash

fallocate -l 10G bar

for i in {1..100}
do
   echo "copy file $i times"
#   scp SpeedTest_2048MB.dat\?_ga\=2.214932319.973892181.1585884968-607421180.1585884968 root@dahu-31.grenoble.grid5000.fr:/root &
 
#  scp SpeedTest_2048MB.dat\?_ga\=2.214932319.973892181.1585884968-607421180.1585884968 root@dahu-2.grenoble.grid5000.fr:/root &
 #  scp SpeedTest_2048MB.dat\?_ga\=2.214932319.973892181.1585884968-607421180.1585884968 root@dahu-11.grenoble.grid5000.fr:/root
    scp ~/Taxi-Workflow/bar root@dahu-9.grenoble.grid5000.fr:/root/Taxi-Workflow/
done
