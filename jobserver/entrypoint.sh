#!/bin/sh
cat /cromwell.conf | sed -E "s|(password = )\"(.*)\"|\1\"$MYSQL_PASSWORD\"|g" > /cromwell.conf
java -Dconfig.file=/cromwell.conf -jar cromwell-34.jar server
