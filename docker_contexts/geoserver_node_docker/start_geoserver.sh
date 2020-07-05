#!/bin/bash -x
export GEOSERVER_HOME=/opt/tomcat/webapps/geoserver
export JAVA_OPTS="-Xms2g -Xmx${GEOSERVER_MAX_RAM} -XX:SoftRefLRUPolicyMSPerMB=36000 -server -XX:+UseParallelGC -DGEOSERVER_DATA_DIR=${GEOSERVER_DATA_DIR}"
export JAVA_BIN=/usr/bin/java

cd $GEOSERVER_HOME
/opt/tomcat/bin/catalina.sh run
