FROM wsubirg/tinyconda
ADD environment.yml /tmp
RUN conda env create -f /tmp/environment.yml
RUN rm /tmp/environment.yml

RUN apt-get -y update && apt-get -y install wget git
RUN /bin/bash -c "source activate serverenv && pip install git+https://github.com/BiRG/cwltool.git"
RUN /bin/bash -c "source activate serverenv && pip install cwlref-runner"

RUN wget --quiet https://get.docker.com/builds/Linux/x86_64/docker-1.13.1.tgz -O docker.tgz
RUN tar xvf docker.tgz
RUN ln -s /docker/docker /usr/bin/docker

ADD workflow-service /app/
ADD tools/*.py /usr/local/bin/
RUN chmod +x /usr/local/bin/*.py

ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
