#!/bin/bash
cd /omics_dashboard/data_tools/database/ && python3 initdb.py /data/omics.db
mkdir -p /data/samples /data/logs /data/collections /data/workflows
touch /data/logs/omics.log
rm -rf /tmp/*
mkdir -p /tmp/uploads
uwsgi --ini /omics_dashboard/uwsgi.ini
