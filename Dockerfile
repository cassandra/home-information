# Pin specific Python version for consistency across platforms
FROM python:3.11.8-bookworm

# Install dependencies with curl for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        supervisor \
        nginx \
        redis-server \
        redis-tools \
    && mkdir -p /var/log/supervisor \
    && mkdir -p /etc/supervisor/conf.d \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip

WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/src

EXPOSE 8000

VOLUME /data/database /data/media
RUN mkdir -p /data/database && mkdir -p /data/media

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Assumes base.txt is all that is needed (ignores dev-specific dependencies)
COPY src/hi/requirements/base.txt /src/requirements.txt
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

COPY package/docker_supervisord.conf /etc/supervisor/conf.d/hi.conf
COPY package/docker_nginx.conf /etc/nginx/sites-available/default

# Clean up nginx default configurations and ensure proper symlinks
RUN rm -f /etc/nginx/conf.d/default.conf \
    && rm -f /etc/nginx/sites-enabled/default \
    && ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default \
    && nginx -t

COPY package/docker_entrypoint.sh /src/entrypoint.sh
RUN chmod +x /src/entrypoint.sh

COPY src /src
RUN chmod +x /src/bin/docker-start-gunicorn.sh

ENTRYPOINT ["/src/entrypoint.sh"]

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf" ]
