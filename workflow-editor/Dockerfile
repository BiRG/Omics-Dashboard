FROM node:10-stretch
ADD * /workflow-editor
WORKDIR /workflow-editor
RUN npm install
RUN cat app/environments/environment.ts | sed -E "s|(omicsUrl: )'(.*)'|\1'$OMICSSERVER'|g;" > app/environments/environment.ts
RUN cat app/environments/environment.prod.ts | sed -E "s|(omicsUrl: )'(.*)'|\1'$OMICSSERVER'|g;" > app/environments/environment.prod.ts
ENTRYPOINT ["ng", "serve"]
