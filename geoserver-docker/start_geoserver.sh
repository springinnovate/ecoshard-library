#!/bin/bash -x
export GEOSERVER_HOME=/usr/local/geoserver
export GEOSERVER_DATA_DIR=/usr/local/geoserver/data_dir
export JAVA_OPTS="-Xms128m -Xmx2g -XX:SoftRefLRUPolicyMSPerMB=36000"
cd $GEOSERVER_HOME
cmd=java "$JAVA_OPTS" -DGEOSERVER_DATA_DIR="$GEOSERVER_DATA_DIR" -Djava.awt.headless=true -DSTOP.PORT=8079 -DSTOP.KEY=geoserver -jar start.jar
nohup $cmd > log.txt &
bash
