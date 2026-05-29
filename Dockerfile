FROM python:3.14-slim

# renovate: github-releases depName=typst/typst
ARG TYPST_VERSION=0.14.2

WORKDIR /usr/src

COPY build/*.whl .
COPY typarr/gitattributes /etc/gitattributes
RUN apt-get update && apt-get install -y --no-install-recommends curl git git-lfs xz-utils \
    && pip install --no-cache-dir *.whl \
    && rm -f *.whl \
    && curl -sSfL https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz \
       | tar -xJ --strip-components=1 -C /usr/local/bin typst-x86_64-unknown-linux-musl/typst \
    && git lfs install --system \
    && git config --system core.attributesFile /etc/gitattributes \
    && apt-get purge -y --auto-remove xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r -g 1234 typarr \
    && useradd -r -u 1234 -g 1234 -d /typarr -m typarr \
    && mkdir -p /data \
    && chown typarr: /data

USER typarr

WORKDIR /typarr

VOLUME /data

ENV TYPARR_DATA_DIR=/data
ENV XDG_CACHE_HOME=/tmp/.cache

EXPOSE 5000

HEALTHCHECK --start-period=10s --start-interval=2s --interval=10s --timeout=10s --retries=3 \
    CMD curl -sfL http://127.0.0.1:5000/health

ENTRYPOINT ["gunicorn"]
CMD ["-k", "uvicorn.workers.UvicornWorker", "-w", "1", "-b", "0.0.0.0:5000", "--worker-tmp-dir", "/tmp", "--chdir", "/tmp", "typarr:create_app()"]
