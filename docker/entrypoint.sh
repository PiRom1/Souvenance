#!/bin/sh
# Démarrage : migrations, fichiers statiques, puis le serveur.
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
exec gunicorn Souvenance.wsgi:application --bind 0.0.0.0:8000 \
     --worker-class gthread --workers 2 --threads 4 --timeout 600 \
     --access-logfile - --error-logfile -
