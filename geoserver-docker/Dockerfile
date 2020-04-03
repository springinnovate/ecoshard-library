FROM debian:buster

RUN apt-get update
apt-get install -y \
    openjdk-11-jdk \
    libspatialindex-c4v5 \
    git \
    unzip

echo export JAVA_OPTS=\"-Xmx4g\" >> /root/.bashrc
WORKDIR /usr/local/geoserver
COPY geoserver-2.16.2-bin.zip .
RUN unzip geoserver-2.16.2-bin.zip
WORKDIR /usr/local/geoserver/geoserver-2.16.2
ENTRYPOINT ["/usr/local/geoserver/bin/startup.sh"]
