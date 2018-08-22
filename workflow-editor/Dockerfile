FROM node:10-stretch
ADD * /workflow-editor
WORKDIR /workflow-editor
RUN npm install
ADD entrypoint.sh /
RUN chmod +x entrypoint.sh
ENTRYPOINT entrypoint.sh
