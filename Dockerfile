FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SECRET_KEY=build-time-placeholder \
    DJANGO_ALLOWED_HOSTS=*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN python manage.py migrate && \
    python manage.py loaddata data/stations_fixture.json

EXPOSE 8080

CMD ["gunicorn", "fuelroute.wsgi", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "300", "--graceful-timeout", "300"]
