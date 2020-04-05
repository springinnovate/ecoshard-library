#!/bin/bash
export GEOSERVER_HOME=/usr/local/geoserver
export GEOSERVER_DATA_DIR=/mnt/data_dir
export JAVA_OPTS=-Xmx2g
cd $GEOSERVER_HOME
exec java $JAVA_OPTS -DGEOSERVER_DATA_DIR="$GEOSERVER_DATA_DIR" -Djava.awt.headless=true -DSTOP.PORT=8079 -DSTOP.KEY=geoserver -jar start.jar
