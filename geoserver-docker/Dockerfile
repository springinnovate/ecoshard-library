# This is stac-geoserver-api:1
FROM debian:10.3

RUN apt-get update
RUN apt-get install -y \
    software-properties-common \
    wget
RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN apt-get update && apt-get upgrade -y

RUN apt-get install -y \
    gcc \
    git \
    libffi-dev \
    openjdk-11-jdk \
    unzip

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

RUN apt-get install -y \
    emacs \
    python3-pip \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    python3-dev \
    python3-setuptools

RUN pip3 install --no-cache-dir \
    Cython \
    flask \
    matplotlib \
    numpy \
    requests \
    retrying \
    rtree \
    scipy \
    shapely \
    git+https://github.com/natcap/pygeoprocessing.git@release/2.0

RUN apt install curl -y
SHELL ["/bin/bash", "-c"]
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
