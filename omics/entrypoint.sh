#!/bin/bash
source activate serverenv
uwsgi --ini /app/uwsgi.ini 
