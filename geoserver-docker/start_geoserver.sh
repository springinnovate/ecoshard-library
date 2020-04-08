#!/bin/bash -x
export GEOSERVER_HOME=/usr/local/geoserver
export GEOSERVER_DATA_DIR=/usr/local/geoserver/data_dir
export JAVA_OPTS="-Xms512m -Xmx2g -XX:SoftRefLRUPolicyMSPerMB=36000"
export JAVA_BIN=/usr/bin/java
cd $GEOSERVER_HOME
nohup $JAVA_BIN $JAVA_OPTS -DGEOSERVER_DATA_DIR=$GEOSERVER_DATA_DIR -Djava.awt.headless=true -DSTOP.PORT=8079 -DSTOP.KEY=geoserver -jar start.jar > geo_log.txt &
touch geo_log.txt
tail -n +0 --pid=$$ -f ./geo_log.txt | { sed "/Server:main: Started/ q" && kill $$ ;}
cd bin
python3 geoserver_flask_manager.py http://localhost:8080 geoserver
bash
