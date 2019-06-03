FROM node:8-slim
ARG OMICSSERVER
ADD workflow-editor /app
WORKDIR /app
RUN sed -ri "s|(omicsUrl: )'(.*)'|\1'"$OMICSSERVER"'|g" src/environments/environment.prod.ts
RUN npm install
RUN /app/node_modules/@angular/cli/bin/ng build --prod --deployUrl=/omics/static/workflow_editor/ --baseHref=/omics/static/workflow_editor/

FROM python:3.7-slim
ARG WWW_UID
RUN pip install --upgrade pip
RUN apt update && apt install -y apt-transport-https ca-certificates wget gnupg --no-install-recommends
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN echo "deb https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
RUN apt -y update && apt -y install build-essential gcc gfortran libpcre3-dev libmagic1 wget xvfb xauth libgtk2.0-0 libgconf-2-4 google-chrome-stable poppler-utils inkscape --no-install-recommends
RUN wget https://github.com/plotly/orca/releases/download/v1.2.1/orca-1.2.1-x86_64.AppImage
RUN chmod +x orca-1.2.1-x86_64.AppImage
RUN ./orca-1.2.1-x86_64.AppImage --appimage-extract
RUN rm -rf orca-1.2.1-x86_64.AppImage
RUN mv /squashfs-root/app /orca
RUN mv /squashfs-root/usr/lib/* /usr/lib
#RUN mv /squashfs-root/usr/share/icons/* /usr/share/icons
RUN rm -rf /squashfs-root
RUN echo '#!/bin/bash' >> /usr/bin/orca && echo 'xvfb-run -a /orca/orca "$@"' >> /usr/bin/orca
RUN chmod +x /usr/bin/orca
ADD omics_dashboard/requirements.txt .
RUN pip install -r requirements.txt
RUN rm requirements.txt
ADD omics_dashboard /omics_dashboard/
COPY --from=0 /app/dist/workflow-editor /omics_dashboard/static/workflow_editor/
RUN rm -rf /var/lib/apt/lists/*
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
RUN groupmod -g $WWW_UID www-data
RUN usermod -u $WWW_UID www-data
USER www-data
ENTRYPOINT ["/entrypoint.sh"]
