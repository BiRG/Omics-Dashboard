#!/bin/bash
rq worker flask-task high default low --path /omics_dashboard --url redis://redis/0
