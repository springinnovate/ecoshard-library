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

RUN mkdir -p /usr/local/stac_manager

WORKDIR /usr/local/stac_manager
COPY requirements.txt /usr/local/stac_manager/
RUN pip3 install -r requirements.txt

COPY . /usr/local/stac_manager/
RUN rm start_stac_api.sh
RUN pip3 install -e .

COPY start_stac_api.sh /usr/local/stac_manager/
EXPOSE ${API_HOST_PORT}
