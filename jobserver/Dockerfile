FROM python:3.7-slim
ARG MYSQL_PASSWORD
RUN mkdir -p /usr/share/man/man1
RUN apt -y update && apt -y install wget openjdk-8-jre-headless 
RUN apt -y update && apt -y install build-essential gcc gfortran
RUN apt -y update && apt -y install mysql-client
RUN pip install --upgrade pip
ADD requirements.txt .
RUN pip install -r requirements.txt
#RUN pip install git+https://github.com/BiRG/cwltool.git

RUN wget https://github.com/broadinstitute/cromwell/releases/download/34/cromwell-34.jar

RUN wget --quiet https://get.docker.com/builds/Linux/x86_64/docker-1.13.1.tgz -O docker.tgz
RUN tar xvf docker.tgz
RUN ln -s /docker/docker /usr/bin/docker

#ADD tools/*.py /usr/local/bin/
#RUN chmod +x /usr/local/bin/*.py
ADD cromwell.conf /
RUN sed -ri "s|(password = )\"(.*)\"|\1\""$MYSQL_PASSWORD"\"|g" /cromwell.conf
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENV PATH="/modules/sbin:/modules/bin:${PATH}"
USER www-data
ENTRYPOINT /entrypoint.sh
