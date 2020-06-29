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
RUN mkdir -p /usr/local/stac_manager

COPY . /usr/local/stac_manager/
WORKDIR /usr/local/stac_manager
RUN pip3 install -r requirements.txt
RUN pip3 install -e .

WORKDIR /usr/local/stac_manager/stac_api
EXPOSE 8888
ENTRYPOINT ["bash",  "-i", "/usr/local/stac_manager/start_stac_manager.sh"]
