FROM ubuntu:xenial
RUN apt -y update
RUN apt -y install wget
RUN apt -y install docker.io
RUN wget https://github.com/ohsu-comp-bio/funnel/releases/download/0.2.0/funnel-linux-amd64.tar.gz
RUN tar xvf funnel-linux-amd64.tar.gz
RUN mv funnel-linux-amd64 /bin/funnel

