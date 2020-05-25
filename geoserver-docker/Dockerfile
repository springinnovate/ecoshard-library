# Install GeoServer and supporing Python libraries
FROM therealspring/python-gdal:3.0.4

RUN apt-get install -y openjdk-11-jdk-headless

RUN apt-get install -y \
    emacs \
    openjdk-11-jdk

RUN apt update -y && apt upgrade -y
RUN apt install libspatialindex-dev -y

RUN apt install python3-pip -y
RUN pip3 install --no-cache-dir \
    Cython \
    flask \
    matplotlib \
    requests \
    retrying \
    rtree \
    scipy \
    shapely

RUN apt install -y \
    openssl \
    curl
SHELL ["/bin/bash", "-c"]
WORKDIR /usr/local/gcloud-sdk
RUN wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-284.0.0-linux-x86_64.tar.gz && tar -xvzf google-cloud-sdk-284.0.0-linux-x86_64.tar.gz
RUN ./google-cloud-sdk/install.sh
RUN source /usr/local/gcloud-sdk/google-cloud-sdk/completion.bash.inc
RUN source /usr/local/gcloud-sdk/google-cloud-sdk/path.bash.inc
RUN echo "export PATH=$PATH:/usr/local/gcloud-sdk/google-cloud-sdk/bin" >> /root/.bashrc

COPY salo-api-5de978810708.json /usr/local/salo-api-5de978810708.json
RUN /usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file=/usr/local/salo-api-5de978810708.json
RUN rm /usr/local/salo-api-5de978810708.json

WORKDIR /usr/local
COPY geoserver-2.17.0-bin.zip .
RUN unzip geoserver-2.17.0-bin.zip -d geoserver
RUN rm geoserver-2.17.0-bin.zip
# We'll mount our own data dir so don't use the default
RUN rm -rf geoserver/data_dir/*

RUN apt install git -y
RUN pip3 install pygeoprocessing==2.0.0
RUN pip3 install ecoshard==0.4.0

COPY start_geoserver.sh /usr/local/geoserver/bin
COPY api_key_manager.py /usr/local/geoserver/bin
COPY styles/ /usr/local/geoserver/bin/styles/

RUN pip3 install waitress
COPY stac_api /usr/local/geoserver/bin/stac_api
COPY setup.py /usr/local/geoserver/bin
WORKDIR /usr/local/geoserver/bin/
RUN pip3 install -e .

RUN useradd -r -m -U -d /opt/tomcat -s /bin/false tomcat
COPY apache-tomcat-9.0.35.tar.gz .
RUN tar xf apache-tomcat-9.0.35.tar.gz -C /opt/tomcat
COPY tomcat.service /etc/systemd/system/tomcat.service
RUN systemctl enable tomcat
RUN systemctl start tomcat

WORKDIR /usr/local/geoserver
ENTRYPOINT ["bash",  "-i", "/usr/local/geoserver/bin/start_geoserver.sh"]
