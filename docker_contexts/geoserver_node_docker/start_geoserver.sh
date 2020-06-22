geoserver-docker/start_geoserver.sh
#!/bin/bash -x
# $1 -- max ram in g (i.e. 5g)
export GEOSERVER_HOME=/usr/local/geoserver
export GEOSERVER_DATA_DIR=${GEOSERVER_HOME}/data_dir
export JAVA_OPTS="-Xms2g -Xmx$1 -XX:SoftRefLRUPolicyMSPerMB=36000 -server -XX:+UseParallelGC -DGEOSERVER_DATA_DIR=$GEOSERVER_DATA_DIR"
export JAVA_BIN=/usr/bin/java

cd $GEOSERVER_HOME
/opt/tomcat/bin/catalina.sh run > tomcatlog.txt