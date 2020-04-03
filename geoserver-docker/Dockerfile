FROM debian:buster

RUN apt-get update
RUN apt-get install -y \
    git \
    libspatialindex-c4v5 \
    openjdk-11-jdk \
    unzip

RUN echo export JAVA_OPTS=\"-Xmx4g\" >> /root/.bashrc
WORKDIR /usr/local/geoserver
COPY geoserver-2.16.2-bin.zip .
RUN unzip geoserver-2.16.2-bin.zip
WORKDIR /usr/local/geoserver/geoserver-2.16.2
ENTRYPOINT ["/usr/local/geoserver/bin/startup.sh"]
