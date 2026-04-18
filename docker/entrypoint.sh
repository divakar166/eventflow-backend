#!/bin/bash
set -e

echo "Waiting for postgres..."
while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do
  sleep 1
done

echo "Running shared migrations..."
uv run python manage.py migrate_schemas --shared

echo "Running tenant migrations..."
uv run python manage.py migrate_schemas

echo "Starting server..."
exec "$@"