FROM ubuntu:18.04

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y \
    git \
    openjdk-11-jdk \
    software-properties-common \
    unzip

RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable
RUN apt-get update
RUN apt-get install -y \
    build-essential \
    gdal=3.0.4+dfsg-1~bionic0 \
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
