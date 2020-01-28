FROM node:8-slim
ARG OMICSSERVER
ADD workflow-editor /app
WORKDIR /app
RUN sed -ri "s|(omicsUrl: )'(.*)'|\1'"$OMICSSERVER"'|g" src/environments/environment.prod.ts
RUN npm install
RUN /app/node_modules/@angular/cli/bin/ng build --prod --deployUrl=/omics/static/workflow_editor/ --baseHref=/omics/static/workflow_editor/

FROM wsubirg/omics-dashboard:omics-cpu

RUN apt -y update && apt -y install libssl-dev --no-install-recommends && rm -rf /var/lib/apt/lists/*

ARG OMICS_UID
ARG OMICS_GID
ADD omics_dashboard/requirements.txt .
RUN pip install -r requirements.txt
RUN rm requirements.txt
COPY --from=0 /app/dist/workflow-editor /omics_dashboard/static/workflow_editor/

RUN groupadd -f -g $OMICS_GID omics
RUN useradd -u $OMICS_UID -g omics omics
RUN echo 'omics ALL= NOPASSWD: /usr/bin/xvfb-run' >> /etc/sudoers
ADD entrypoint.sh /
ADD rq_worker_entrypoint.sh /
RUN chown omics:omics /entrypoint.sh /rq_worker_entrypoint.sh && chmod +x /entrypoint.sh /rq_worker_entrypoint.sh
ADD omics_dashboard /omics_dashboard/
RUN chown -R omics:omics /omics_dashboard 
USER omics

ENV H5PY_DEFAULT_READONLY 1

ENTRYPOINT ["/entrypoint.sh"]
