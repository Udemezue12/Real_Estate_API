
FROM python:3.11-slim


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


RUN apt-get update && apt-get install -y \
    binutils libproj-dev gdal-bin \
    python3-dev libpq-dev gcc postgresql-client supervisor \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app


COPY requirements.txt /app/


RUN pip install --upgrade pip && pip install -r requirements.txt


COPY . /app/


COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf


COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


WORKDIR /app/estate_app


ENTRYPOINT ["/entrypoint.sh"]