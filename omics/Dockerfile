FROM python:3.7-slim
RUN pip install --upgrade pip
RUN apt -y update && apt -y install build-essential gcc gfortran libpcre3-dev
ADD omics_dashboard/requirements.txt .
RUN pip install -r requirements.txt
RUN rm requirements.txt
ADD omics_dashboard /omics_dashboard/
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
