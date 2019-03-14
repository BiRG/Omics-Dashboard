FROM node:8-slim
ARG OMICSSERVER
ADD workflow-editor /app
WORKDIR /app
RUN sed -ri "s|(omicsUrl: )'(.*)'|\1'"$OMICSSERVER"'|g" src/environments/environment.prod.ts
RUN npm install
RUN /app/node_modules/@angular/cli/bin/ng build --prod --deployUrl=/omics/static/workflow_editor/ --baseHref=/omics/static/workflow_editor/

FROM python:3.7-slim
RUN pip install --upgrade pip
RUN apt -y update && apt -y install build-essential gcc gfortran libpcre3-dev libmagic1
ADD omics_dashboard/requirements.txt .
RUN pip install -r requirements.txt
RUN rm requirements.txt
ADD omics_dashboard /omics_dashboard/
COPY --from=0 /app/dist/workflow-editor /omics_dashboard/static/workflow_editor/
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
