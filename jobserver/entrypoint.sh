#!/bin/bash
cat /cromwell.conf | sed -E "s|(password = )\"(.*)\"|\1\"$MYSQL_PASSWORD\"|g" > /cromwell.conf
while ! mysqladmin ping -h"jobserverdb" --silent; do
  echo "Waiting for database."
  sleep 1
done
java -Dconfig.file=/cromwell.conf -jar cromwell-34.jar server
