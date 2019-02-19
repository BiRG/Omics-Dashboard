FROM nginx:alpine
MAINTAINER Daniel P. Foose <dpfoose@gmail.com>
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 8080
EXPOSE 5000
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
