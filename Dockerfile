FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY Pocket_Signal_Analyzer_Fixed_Deployable.zip /tmp/project.zip
RUN apt-get update && apt-get install -y --no-install-recommends unzip && unzip -q /tmp/project.zip -d /tmp/project && cp -a /tmp/project/Pocket_Signal_Analyzer/. /app/ && rm -rf /tmp/project /tmp/project.zip && pip install --no-cache-dir -r requirements.txt && apt-get purge -y unzip && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 60"]