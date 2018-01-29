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

ENV PATH /opt/conda/bin:$PATH
ADD environment.yml /tmp
RUN conda env create -f /tmp/environment.yml
RUN rm /tmp/environment.yml

RUN wget --quiet https://github.com/dpfoose/cwltool https://github.com/dpfoose/cwltool/archive/master.zip
RUN /bin/bash -c "source /opt/conda/bin/activate serverenv && pip install /master.zip &&  rm /master.zip"
#RUN /bin/bash -c "source /opt/conda/bin/activate serverenv && pip install git+https://github.com/dpfoose/cwltool.git"
#RUN /bin/bash -c "source /opt/conda/bin/activate serverenv && pip install cwlref-runner"
ADD cwltool /cwltool
#RUN /bin/bash -c "source /opt/conda/bin/activate serverenv && pip install -e /cwltool"
#RUN /bin/bash -c "source /opt/conda/bin/activate serverenv && pip install cwlref-runner"


RUN wget --quiet https://get.docker.com/builds/Linux/x86_64/docker-1.13.1.tgz -O docker.tgz
RUN tar xvf docker.tgz
RUN ln -s /docker/docker /usr/bin/docker

ADD workflow-service /app/
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
