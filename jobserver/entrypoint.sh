#!/bin/bash
cat /cromwell.conf
while ! mysqladmin ping -h"jobserverdb" --silent; do
  echo "Waiting for database."
  sleep 1
done
java -Dconfig.file=/cromwell.conf -jar cromwell-34.jar server
