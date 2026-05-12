FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Kolkata

RUN apt-get update && apt-get install -y --no-install-recommends \
        tzdata \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        shared-mime-info \
        fonts-dejavu \
        sqlite3 \
        bash \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/share/zoneinfo/$TZ /etc/localtime

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/db /app/data/reports /app/data/excel /app/data/outreach \
             /app/data/content /app/data/tool-research /app/data/profit \
             /app/data/proposals /app/data/exports /app/data/logs

CMD ["python", "-m", "src.orchestrator.main"]
