FROM python:3.7-slim
ADD requirements.txt .
RUN pip install --upgrade pip
RUN apt -y update && apt -y install build-essential gcc gfortran
RUN pip install -r requirements.txt

ADD omics_dashboard /omics_dashboard/
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
