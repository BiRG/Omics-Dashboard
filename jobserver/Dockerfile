FROM ubuntu:xenial
ENV DEBIAN_FRONTEND noninteractive
RUN apt update
RUN apt -y --no-install-recommends install build-essential
RUN apt -y --no-install-recommends install liblapack-dev libopenblas-dev
RUN apt -y install wget bzip2 ca-certificates libglib2.0-0 libxext6 libsm6 libxrender1

RUN apt-get install -y wget bzip2 ca-certificates \
    libglib2.0-0 libxext6 libsm6 libxrender1

RUN echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/conda.sh
RUN wget --quiet https://repo.continuum.io/miniconda/Miniconda3-4.3.27-Linux-x86_64.sh -O ~/miniconda.sh
RUN /bin/bash ~/miniconda.sh -b -p /opt/conda 
RUN rm ~/miniconda.sh

# Install Docker from Docker Inc. repositories.
# current cwl-runner runs the docker cli instead of communicating via api
RUN apt update && apt -y --no-install-recommends install apt-transport-https ca-certificates curl software-properties-common
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - 
RUN add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) \
    stable"
RUN apt update
RUN apt -y install docker-ce


ENV PATH /opt/conda/bin:$PATH
ADD environment.yml /tmp
RUN conda env create -f /tmp/environment.yml
RUN rm /tmp/environment.yml

ADD workflow-service /app/
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
