FROM ubuntu:18.04

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y \
    git \
    openjdk-11-jdk \
    software-properties-common \
    unzip

RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable
RUN apt-get update
ENTRYPOINT bash
