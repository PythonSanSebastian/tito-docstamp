FROM ubuntu:19.04

RUN apt update && \
    apt install -y wget bash python3.7-venv python3.7-dev python3-pip build-essential inkscape unzip librsvg2-bin

ENV LANG C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LC_ALL C.UTF-8

WORKDIR /root
COPY Pipfile /root
COPY Pipfile.lock /root
ADD fonts /usr/local/share/fonts/

RUN fc-cache -f -v && \
    python3 -m pip install -U pip setuptools pipenv && \
    python3 -m pipenv install

ENTRYPOINT bash
