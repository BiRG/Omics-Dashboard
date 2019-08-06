#!/bin/bash
echo $MYSQL_ROOT_PASSWORD
echo $MYSQL_USER
while ! mysqladmin ping -h"jobserverdb" --silent; do
  echo "Waiting for database."
  sleep 1
done
chmod +x /modules/sbin/* || true
chmod +x /modules/bin/* || true
java -Dconfig.file=/cromwell.conf -jar cromwell-44.jar server
