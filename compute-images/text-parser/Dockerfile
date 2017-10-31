FROM ubuntu:xenial
MAINTAINER Daniel P. Foose <dpfoose@gmail.com>
ENV DEBIAN_FRONTEND noninteractrive
RUN apt-get update
RUN apt-get -y --no-install-recommends install build-essential
RUN apt-get -y --no-install-recommends install python3-dev python3-pip python3-setuptools
RUN apt-get -y --no-install-recommends install libhdf5-dev

ADD src /src
RUN pip3 install --upgrade pip
ENV HDF5_DIR=/usr/lib/x86_64-linux-gnu/hdf5/serial/
RUN pip3 install --upgrade -r /src/requirements.txt

#the entry point will always be python3 followed by the script to run


