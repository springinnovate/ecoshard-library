FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y \
    git \
    openjdk-11-jdk \
    software-properties-common \
    unzip

RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y
RUN apt-get update

RUN apt-get install -y \
    build-essential \
    libgdal-dev=3.0.4+dfsg-1~bionic0 \
    gdal-bin=3.0.4+dfsg-1~bionic0 \
    libgdal-java=3.0.4+dfsg-1~bionic0 \
    libspatialindex-c4v5

RUN echo export JAVA_OPTS=\"-Xmx4g\" >> /root/.bashrc
WORKDIR /usr/local/geoserver
COPY geoserver-2.16.2-bin.zip .
RUN unzip geoserver-2.16.2-bin.zip
WORKDIR /usr/local/geoserver/geoserver-2.16.2

ENTRYPOINT ["/usr/local/geoserver/bin/startup.sh"]
ENTRYPOINT bash
