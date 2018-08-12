#!/bin/bash
cd /app/database/ && python3 /app/data_tools/database/initdb.py /data/omics.db
mkdir -p /data/samples /data/logs /data/collections /data/workflows
mkdir -p /tmp/uploads
uwsgi --ini /omics_dashboard/uwsgi.ini