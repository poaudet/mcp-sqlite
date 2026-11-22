FROM python:3.12-slim

RUN pip install --no-cache-dir "mcp>=1.9.0,<2.0.0"

WORKDIR /app
COPY server.py .

RUN mkdir -p /data
EXPOSE 8000

CMD ["python", "server.py"]
