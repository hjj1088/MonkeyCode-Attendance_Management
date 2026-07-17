FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY lib/ lib/
COPY shared/ shared/
COPY *.html .
COPY export_server.py .
COPY version.py version_stub.py

ARG GIT_SHA=unknown
ARG BUILD_TIME=unknown
RUN echo "GIT_SHA = '${GIT_SHA}'" > version.py && \
    echo "BUILD_TIME = '${BUILD_TIME}'" >> version.py

EXPOSE 8000

ENV PORT=8000

CMD ["python3", "export_server.py"]
