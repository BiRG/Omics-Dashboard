# Job Server

This runs the [Funnel](https://ohsu-comp-bio.github.io/funnel) jobserver
in a Docker container. For this to work properly, you must bind mount
/var/run/docker.sock

This is completely unauthenticated. It is designed to be used by other
containers in a docker network (such as the one created by docker compose)


