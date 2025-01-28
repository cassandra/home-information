FROM python:3.11

RUN apt-get update \
    && apt-get install -y --no-install-recommends supervisor nginx redis-server \
    && mkdir -p /var/log/supervisor \
    && mkdir -p /etc/supervisor/conf.d \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /src

RUN pip install --upgrade pip

# Assumes base.txt is all that is needed (ignores dev-specific dependencies)
COPY src/hi/requirements/base.txt /src/requirements.txt
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

COPY packaging/supervisor-interface.conf /etc/supervisor/conf.d/waa-interface.conf
COPY packaging/nginx-interface.conf /etc/nginx/sites-available/default

COPY src /src

EXPOSE 8000

VOLUME /data/database
RUN mkdir -p /data/database
VOLUME /data/media
RUN mkdir -p /data/media

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf" ]
