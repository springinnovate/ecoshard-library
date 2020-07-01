FROM python:3.8.3-buster

RUN apt update && apt upgrade -y
RUN apt install -y \
    python3-pip

WORKDIR /usr/local/expand_drive_service
COPY . /usr/local/expand_drive_service
RUN pip3 install -r requirements

EXPOSE ${DISK_RESIZE_SERVICE_PORT}
ENTRYPOINT ["./expand_drive_serivce.py"]
