FROM python:3.14-slim

# renovate: github-releases depName=typst/typst
ARG TYPST_VERSION=0.14.2

# Provided by BuildKit (amd64, arm64, …).
ARG TARGETARCH

WORKDIR /usr/src

COPY build/*.whl .
COPY tino/gitattributes /etc/gitattributes
RUN apt-get update && apt-get install -y --no-install-recommends curl git git-lfs xz-utils \
    && pip install --no-cache-dir *.whl \
    && rm -f *.whl \
    && case "${TARGETARCH}" in \
         amd64) TYPST_ARCH=x86_64 ;; \
         arm64) TYPST_ARCH=aarch64 ;; \
         *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
       esac \
    && curl -sSfL "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${TYPST_ARCH}-unknown-linux-musl.tar.xz" \
       | tar -xJ --strip-components=1 -C /usr/local/bin "typst-${TYPST_ARCH}-unknown-linux-musl/typst" \
    && git lfs install --system \
    && git config --system core.attributesFile /etc/gitattributes \
    && apt-get purge -y --auto-remove xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r -g 1234 tino \
    && useradd -r -u 1234 -g 1234 -d /tino -m tino \
    && mkdir -p /data \
    && chown tino: /data

USER tino

WORKDIR /tino

VOLUME /data

ENV TINO_DATA_DIR=/data
ENV XDG_CACHE_HOME=/tmp/.cache

EXPOSE 5000

HEALTHCHECK --start-period=10s --start-interval=2s --interval=10s --timeout=10s --retries=3 \
    CMD curl -sfL http://127.0.0.1:5000/health

ENTRYPOINT ["gunicorn"]
CMD ["-k", "uvicorn.workers.UvicornWorker", "-w", "1", "-b", "0.0.0.0:5000", "--worker-tmp-dir", "/tmp", "--chdir", "/tmp", "tino:create_app()"]
