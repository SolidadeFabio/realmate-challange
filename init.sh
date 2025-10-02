#!/bin/bash

echo "Starting Django initialization..."

echo "Waiting for PostgreSQL to be ready..."
while ! PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"

echo "Creating migrations..."
poetry run python manage.py makemigrations --noinput

echo "Applying migrations..."
poetry run python manage.py migrate --noinput

echo "Checking for superuser..."
poetry run python manage.py shell << EOF
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser created: username={username}')
else:
    print(f'Superuser {username} already exists')
EOF

echo "Collecting static files..."
poetry run python manage.py collectstatic --noinput || true

echo "Initialization complete!"

echo "Starting Django server..."
exec poetry run python manage.py runserver 0.0.0.0:80