FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY lib/ lib/
COPY shared/ shared/
COPY *.html .
COPY export_server.py .

EXPOSE 8000

ENV PORT=8000

CMD ["python3", "export_server.py"]
