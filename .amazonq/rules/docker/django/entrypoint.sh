#!/bin/bash
set -e

echo "⏳ Aguardando PostgreSQL..."
while ! nc -z db 5432; do
  sleep 1
done
echo "✅ PostgreSQL disponível!"

echo "⏳ Aguardando Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "✅ Redis disponível!"

echo "🔄 Executando migrações..."
python manage.py migrate --noinput

echo "📊 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "🚀 Iniciando aplicação Django..."
exec "$@"