FROM nginx:alpine
MAINTAINER Daniel P. Foose <dpfoose@gmail.com>
COPY nginx.conf /etc/nginx/nginx.conf
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
RUN set -x ; \
      addgroup -g 82 -S www-data ; \
      adduser -u 82 -D -S -G www-data www-data && exit 0 ; exit 1
EXPOSE 8080
EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
