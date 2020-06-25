FROM python:3.8.3-buster

RUN apt update && apt upgrade -y
RUN apt install python3-pip -y
RUN pip3 install sqlalchemy

WORKDIR /usr/local/test
COPY . /usr/local/test/
ENTRYPOINT ["python3", "test.py"]
