# Container for STAC API manager
FROM therealspring/python-gdal:3.0.4

RUN apt-get update -qq && \
    apt-get install -y \
    emacs \
    libspatialindex-dev \
    python3-pip \
    postgresql-client \
    openssl \
    curl \
    git \
    && \
    rm -rf /var/lib/apt/lists/*

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

RUN mkdir -p /usr/local/stac_manager

COPY start_stac_manager.sh /usr/local/stac_manager/
COPY api_key_manager.py /usr/local/stac_manager/
COPY geoserver_styles /usr/local/stac_manager/geoserver_styles/

COPY stac_api /usr/local/stac_api/
COPY setup.py /usr/local/stac_api/
COPY requirements.txt /usr/local/stac_api/
RUN pip3 install -r requirements.txt
RUN pip3 install -e .

WORKDIR /usr/local/stac_api
EXPOSE 8888
ENTRYPOINT ["bash",  "-i", "/usr/local/geoserver/bin/launch_stac_manager.sh"]
