#!/bin/bash -x
# $1 -- API host
# $2 -- API port
# $3 -- GEOSERVER host
# $4 -- GEOSERVER port
# $5 -- max ram in g (i.e. 55g)
# $6 -- authorization database password
# $7 -- authorization database host
export GEOSERVER_HOME=/usr/local/geoserver
export GEOSERVER_DATA_DIR=${GEOSERVER_HOME}/data_dir
export JAVA_OPTS="-Xms2g -Xmx$5 -XX:SoftRefLRUPolicyMSPerMB=36000 -server -XX:+UseParallelGC -DGEOSERVER_DATA_DIR=$GEOSERVER_DATA_DIR"
export JAVA_BIN=/usr/bin/java

cd $GEOSERVER_HOME
echo $JAVA_OPTS >> java_opts.txt

touch bin/nohup.out
nohup /opt/tomcat/bin/catalina.sh run > tomcatlog.txt &
cd bin

touch stac_api/config.py
echo "SERVER_NAME = '$1:$2'" > stac_api/config.py
echo "GEOSERVER_HOST = '$3:$4'" >> stac_api/config.py
echo "SECRET_KEY = 'none'" >> stac_api/config.py
echo "SQLALCHEMY_DATABASE_URI = 'postgresql://salo-api-user:$6@$7/salo-api-auth'" >> stac_api/config.py
nohup waitress-serve --listen=0.0.0.0:$2 --call stac_api:create_app &
