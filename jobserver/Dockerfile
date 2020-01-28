FROM wsubirg/omics-dashboard:jobserver-cpu
ARG MYSQL_PASSWORD
ARG OMICS_UID
ARG OMICS_GID

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD cromwell.conf /
RUN sed -ri "s|(password = )\"(.*)\"|\1\""$MYSQL_PASSWORD"\"|g" /cromwell.conf
RUN cat /cromwell.conf
ENV PATH="/modules/sbin:/modules/bin:${PATH}"
RUN groupadd -f -g $OMICS_GID omics
RUN useradd -u $OMICS_UID -g omics omics

ADD entrypoint.sh /
RUN chown omics:omics /entrypoint.sh /cromwell.conf /usr/bin/cromwell-44.jar && chmod +x /entrypoint.sh
RUN touch /var/log/nvblas.log && chown omics:omics /var/log/nvblas.log

USER omics
ENTRYPOINT /entrypoint.sh
