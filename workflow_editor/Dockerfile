FROM node:8-slim
ADD workflow-editor /app
ADD entrypoint.sh .
WORKDIR /app
RUN npm install
RUN npm run-script build --prod
RUN chmod +x /entrypoint.sh
ENTRYPOINT /entrypoint.sh
