# This is stac-geoserver-api:1
FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y \
    gcc \
    git \
    libffi-dev \
    openjdk-11-jdk \
    python3-dev \
    python3-setuptools \
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

RUN pip3 install --no-cache-dir \
    Cython \
    flask \
    matplotlib \
    numpy \
    requests \
    retrying \
    rtree \
    scipy \
    shapely

WORKDIR /usr/local/gcloud-sdk
RUN curl https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-284.0.0-linux-x86_64.tar.gz?hl=id | tar -xvzf -
RUN ./google-cloud-sdk/install.sh
RUN source /usr/local/gcloud-sdk/google-cloud-sdk/completion.bash.inc
RUN source /usr/local/gcloud-sdk/google-cloud-sdk/path.bash.inc
RUN echo "export PATH=$PATH:/usr/local/gcloud-sdk/google-cloud-sdk/bin" >> /root/.bashrc

COPY salo-api-5de978810708.json /usr/local/salo-api-5de978810708.json
RUN /usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file=/usr/local/salo-api-5de978810708.json
RUN /usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud config set project natgeo-dams
RUN rm /usr/local/salo-api-5de978810708.json

COPY start_geoserver.sh /usr/local/geoserver/bin
COPY geoserver_flask_manager.py /usr/local/geoserver/bin
COPY geoserver_tracer.py /usr/local/geoserver/bin

WORKDIR /usr/local/geoserver
ENTRYPOINT ["bash",  "-i", "/usr/local/geoserver/bin/start_geoserver.sh"]
