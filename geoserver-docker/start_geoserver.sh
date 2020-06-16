#!/bin/bash -x
# $1 -- internal API host
# $2 -- internal API port
# $3 -- external API host:port
# $4 -- GEOSERVER host
# $5 -- GEOSERVER port
# $6 -- max ram in g (i.e. 55g)
# $7 -- authorization database password
# $8 -- authorization database host
export GEOSERVER_HOME=/usr/local/geoserver
export GEOSERVER_DATA_DIR=${GEOSERVER_HOME}/data_dir
export JAVA_OPTS="-Xms2g -Xmx$6 -XX:SoftRefLRUPolicyMSPerMB=36000 -server -XX:+UseParallelGC -DGEOSERVER_DATA_DIR=$GEOSERVER_DATA_DIR"
export JAVA_BIN=/usr/bin/java

# cd $GEOSERVER_HOME
# echo $JAVA_OPTS >> java_opts.txt

# touch bin/nohup.out
# nohup /opt/tomcat/bin/catalina.sh run > tomcatlog.txt &
cd bin

touch stac_api/config.py
echo "SERVER_NAME = '$1:$2'" > stac_api/config.py
echo "EXTERNAL_API_HOST = '$3'"
echo "GEOSERVER_HOST = '$4:$5'" >> stac_api/config.py
echo "SECRET_KEY = 'none'" >> stac_api/config.py
echo "SQLALCHEMY_DATABASE_URI = 'postgresql://salo-api-user:$7@$8/salo-api-auth'" >> stac_api/config.py
waitress-serve --listen=0.0.0.0:$2 --call stac_api:create_app
