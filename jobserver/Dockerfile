FROM python:3.7-slim
ARG MYSQL_PASSWORD
ARG OMICS_UID
ARG OMICS_GID
RUN mkdir -p /usr/share/man/man1
RUN apt -y update && apt -y install wget openjdk-8-jre-headless build-essential gcc gfortran mysql-client git \
      && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip
ADD requirements.txt .
RUN pip install -r requirements.txt

ADD cromwell.conf /
RUN sed -ri "s|(password = )\"(.*)\"|\1\""$MYSQL_PASSWORD"\"|g" /cromwell.conf
RUN cat /cromwell.conf
ENV PATH="/modules/sbin:/modules/bin:${PATH}"
RUN groupadd -f -g $OMICS_GID omics
RUN useradd -u $OMICS_UID -g omics omics

ADD entrypoint.sh /
ADD https://github.com/broadinstitute/cromwell/releases/download/44/cromwell-44.jar /usr/bin
RUN chown omics:omics /entrypoint.sh /cromwell.conf /usr/bin/cromwell-44.jar && chmod +x /entrypoint.sh
RUN touch /var/log/nvblas.log && chown omics:omics /var/log/nvblas.log

ADD https://download.docker.com/linux/static/stable/x86_64/docker-19.03.1.tgz .
RUN tar -C /usr/bin -xvf docker-19.03.1.tgz --strip 1 && rm docker-19.03.1.tgz

USER omics
ENTRYPOINT /entrypoint.sh
