#!/bin/bash
set -e

echo "Aguardando PostgreSQL..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL disponivel!"

echo "Aguardando Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis disponivel!"

echo "Executando migracoes..."
python manage.py migrate --noinput

if [ "$DEBUG" = "False" ]; then
  echo "Coletando arquivos estaticos..."
  python manage.py collectstatic --noinput
else
  echo "Pulando collectstatic (DEBUG=True)"
fi

echo "Iniciando aplicacao Django..."
exec "$@"