FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y \
    software-properties-common
RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y
RUN apt-get update
ENTRYPOINT bash
