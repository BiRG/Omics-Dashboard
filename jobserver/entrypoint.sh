#!/usr/bin/env bash
while ! mysqladmin ping -h"jobserverdb" --silent; do
  echo "Waiting for database."
  sleep 1
done
chmod +x /modules/sbin/* || true
chmod +x /modules/bin/* || true
java -Dconfig.file=/cromwell.conf -jar /usr/bin/cromwell-44.jar server
