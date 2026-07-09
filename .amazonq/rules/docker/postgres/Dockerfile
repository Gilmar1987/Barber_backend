FROM postgis/postgis:16-3.4

# Instala dependências para compilar pgvector (incluindo clang para bitcode)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    postgresql-server-dev-16 \
    clang-13 \
    llvm-13 \
    && rm -rf /var/lib/apt/lists/*

# Clona e compila pgvector
RUN git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector

# Script de inicialização para habilitar extensões
RUN echo "CREATE EXTENSION IF NOT EXISTS postgis;" > /docker-entrypoint-initdb.d/10-postgis.sh \
    && echo "CREATE EXTENSION IF NOT EXISTS vector;" > /docker-entrypoint-initdb.d/20-pgvector.sh \
    && chmod +x /docker-entrypoint-initdb.d/*.sh