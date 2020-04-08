# This is stac-geoserver-api:1
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

RUN apt-get update -y
RUN apt-get install software-properties-common -y
RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable
RUN apt-get update -y
RUN apt-get install -y \
    build-essential \
    libspatialindex-c4v5 \
    emacs \
    python3-pip \
    git

RUN apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal

RUN apt install -y \
    libffi-dev \
    python3-setuptools \
    gcc \
    python3-dev

RUN pip3 install --no-cache-dir \
    Cython \
    flask \
    matplotlib \
    numpy \
    requests \
    rtree \
    scipy \
    shapely

RUN pip3 install -y \
    retrying

COPY start_geoserver.sh /usr/local/geoserver/bin
COPY geoserver_flask_manager.py /usr/local/geoserver/bin
WORKDIR /usr/local/geoserver
ENTRYPOINT ["bash",  "-i", "/usr/local/geoserver/bin/start_geoserver.sh"]
