FROM ubuntu:xenial
MAINTAINER Daniel P. Foose <dpfoose@gmail.com>
ENV DEBIAN_FRONTEND noninteractrive
RUN apt-get update
RUN apt-get -y --no-install-recommends install build-essential
RUN apt-get -y --no-install-recommends install liblapack-dev libopenblas-dev

RUN apt-get install -y wget bzip2 ca-certificates \
    libglib2.0-0 libxext6 libsm6 libxrender1

RUN echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/conda.sh
RUN wget --quiet https://repo.continuum.io/miniconda/Miniconda3-4.3.27-Linux-x86_64.sh -O ~/miniconda.sh
RUN /bin/bash ~/miniconda.sh -b -p /opt/conda 
RUN rm ~/miniconda.sh

ENV PATH /opt/conda/bin:$PATH
RUN conda install h5py

ADD src/*.py /usr/local/bin/
RUN chmod +x /usr/local/bin/*.py
