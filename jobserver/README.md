# Job Server

This runs the [wes-servers](https://github.com/common-workflow-language/workflow-service) jobserver
in a Docker container. For this to work properly, you must bind mount
/var/run/docker.sock. The server will look for tool definiitions in /data/modules (which you should also
mount).

This is completely unauthenticated. It is designed to be used by other
containers in a docker network (such as the one created by docker compose)
These other containers should have some sort of authentication.

You should not expose any ports on this container outside a docker network.


