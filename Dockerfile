FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN python manage.py migrate --run-syncdb && \
    python manage.py load_fuel_prices

EXPOSE 8080

CMD ["gunicorn", "fuelroute.wsgi", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120"]
