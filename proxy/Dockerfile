FROM nginx:alpine
ARG OMICS_UID
ARG OMICS_GID
MAINTAINER Daniel P. Foose <dpfoose@gmail.com>
COPY nginx.conf /etc/nginx/nginx.conf
RUN addgroup -g ${OMICS_GID} -S omics && adduser -D -u ${OMICS_UID} -G omics omics
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
EXPOSE 8080
EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
