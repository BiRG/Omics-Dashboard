#!/bin/bash
cat /cromwell.conf
echo $MYSQL_ROOT_PASSWORD
cat /cromwell.conf
while ! mysqladmin ping -h"jobserverdb" --silent; do
  echo "Waiting for database."
  sleep 1
done
chmod +x /modules/sbin/*
chmod +x /modules/bin/*
java -Dconfig.file=/cromwell.conf -jar cromwell-34.jar server
