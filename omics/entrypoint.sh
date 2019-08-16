#!/bin/bash
mkdir -p /data/samples /data/logs /data/collections /data/workflows
touch /data/logs/omics.log
rm -rf /tmp/*
mkdir -p /tmp/uploads
uwsgi --ini /omics_dashboard/uwsgi.ini
