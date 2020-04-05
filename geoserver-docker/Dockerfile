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

RUN mkdir -p /mnt/data_dir

WORKDIR /usr/local
COPY geoserver-2.16.2-bin.zip .
RUN unzip geoserver-2.16.2-bin.zip
RUN rm geoserver-2.16.2-bin.zip
RUN mv ./geoserver-2.16.2 ./geoserver
COPY start_geoserver.sh /usr/local/geoserver/bin

WORKDIR /usr/local/geoserver

ENTRYPOINT ["bash",  "-i", "/usr/local/geoserver/bin/start_geoserver.sh"]
