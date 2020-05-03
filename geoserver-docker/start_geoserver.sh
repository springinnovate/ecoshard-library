#!/bin/bash -x
export GEOSERVER_HOME=/usr/local/geoserver
export GEOSERVER_DATA_DIR=${GEOSERVER_HOME}/data_dir
export JAVA_OPTS="-Xms512m -Xmx11g -XX:SoftRefLRUPolicyMSPerMB=36000"
export JAVA_BIN=/usr/bin/java
export EXTERNAL_IP=$1
cd $GEOSERVER_HOME
touch bin/nohup.out
nohup $JAVA_BIN $JAVA_OPTS -DGEOSERVER_DATA_DIR=$GEOSERVER_DATA_DIR -Djava.awt.headless=true -DSTOP.PORT=8079 -DSTOP.KEY=geoserver -jar start.jar > geo_log.txt &
touch geo_log.txt
tail -n +0 --pid=$$ -f ./geo_log.txt | { sed "/Server:main: Started/ q" && kill $$ ;}
cd bin
nohup python3 geoserver_flask_manager.py --external_ip $EXTERNAL_IP --debug_api_key debug_api &
sleep 2
python3 api_key_manager.py --create --add_permission WRITE:salo READ:salo >> api_key
bash
