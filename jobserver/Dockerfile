FROM python:3.7-slim
RUN mkdir -p /usr/share/man/man1
RUN apt -y update && apt -y install wget openjdk-8-jre-headless 
RUN apt -y update && apt -y install build-essential gcc gfortran
RUN pip install --upgrade pip
ADD requirements.txt .
RUN pip install -r requirements.txt
#RUN pip install git+https://github.com/BiRG/cwltool.git

RUN wget https://github.com/broadinstitute/cromwell/releases/download/34/cromwell-34.jar

RUN wget --quiet https://get.docker.com/builds/Linux/x86_64/docker-1.13.1.tgz -O docker.tgz
RUN tar xvf docker.tgz
RUN ln -s /docker/docker /usr/bin/docker

ADD tools/*.py /usr/local/bin/
RUN chmod +x /usr/local/bin/*.py
ADD cromwell.conf /
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT /entrypoint.sh
