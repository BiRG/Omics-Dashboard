FROM python:3.7-slim
ARG MYSQL_PASSWORD
ARG OMICS_UID
ARG OMICS_GID
RUN mkdir -p /usr/share/man/man1
RUN apt -y update && apt -y install wget openjdk-8-jre-headless build-essential gcc gfortran mysql-client \
      && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip
ADD requirements.txt .
RUN pip install -r requirements.txt

RUN wget https://github.com/broadinstitute/cromwell/releases/download/44/cromwell-44.jar
RUN wget --quiet https://get.docker.com/builds/Linux/x86_64/docker-1.13.1.tgz -O docker.tgz
RUN tar xvf docker.tgz && rm docker.tgz
RUN ln -s /docker/docker /usr/bin/docker

ADD cromwell.conf /
RUN sed -ri "s|(password = )\"(.*)\"|\1\""$MYSQL_PASSWORD"\"|g" /cromwell.conf
RUN cat /cromwell.conf
ENV PATH="/modules/sbin:/modules/bin:${PATH}"
RUN groupadd -f -g $OMICS_GID omics
RUN useradd -u $OMICS_UID -g omics omics
ADD entrypoint.sh /
RUN chown omics:omics /entrypoint.sh /cromwell.conf && chmod +x /entrypoint.sh
USER omics
ENTRYPOINT /entrypoint.sh
