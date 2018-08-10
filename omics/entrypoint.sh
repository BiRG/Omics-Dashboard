#!/bin/bash
cd /app/database/ && python3 /app/database/initdb.py /data/omics.db
mkdir -p /data/samples /data/logs /data/collections
mkdir -p /tmp/uploads
uwsgi --ini /app/uwsgi.ini