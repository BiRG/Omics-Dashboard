FROM wsubirg/tinyconda

ADD environment.yml /tmp
RUN conda env create -f /tmp/environment.yml
RUN rm /tmp/environment.yml

ADD app /app/
ADD entrypoint.sh / 
RUN chmod +x /entrypoint.sh
ADD jobserver.py /
ENTRYPOINT ["/entrypoint.sh"]
