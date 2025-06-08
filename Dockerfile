FROM python:3.9-slim-buster

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    php-cli \
    php-xml \
    php-mbstring \
    golang \
    shfmt \
    autopep8 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L https://cs.symfony.com/download/php-cs-fixer-v3.phar -o /usr/local/bin/php-cs-fixer && \
    chmod +x /usr/local/bin/php-cs-fixer

ENV RUSTUP_HOME=/usr/local/rustup
ENV CARGO_HOME=/usr/local/cargo
ENV PATH=/usr/local/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- --default-toolchain stable --profile minimal -y && \
    rustup component add rustfmt && \
    rm -rf ${RUSTUP_HOME}/tmp && \
    rm -rf ${CARGO_HOME}/registry/index && \
    rm -rf ${CARGO_HOME}/registry/cache && \
    rm -rf ${CARGO_HOME}/git/db

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .