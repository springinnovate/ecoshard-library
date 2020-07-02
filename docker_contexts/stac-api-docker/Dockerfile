# Container for STAC API manager
FROM therealspring/python-gdal:3.0.4

# copy public key authorization for creating signed urls for public file downloads
COPY cfo-public-auth.json /usr/local/cfo-public-auth.json
ENV CFO_PUBLIC_KEY=/usr/local/cfo-public-auth.json

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
RUN cat /run/secrets/service_account_key
RUN /usr/local/gcloud-sdk/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file=/run/secrets/service_account_key

RUN mkdir -p /usr/local/stac_manager

COPY . /usr/local/stac_manager/
WORKDIR /usr/local/stac_manager
RUN pip3 install -r requirements.txt
RUN pip3 install -e .

WORKDIR /usr/local/stac_manager/stac_api
EXPOSE 8888
ENTRYPOINT ["bash",  "-i", "/usr/local/stac_manager/start_stac_manager.sh"]
