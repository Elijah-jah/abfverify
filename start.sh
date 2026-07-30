#!/bin/bash
python manage.py migrate
python manage.py loaddata seed_data.json || true
gunicorn config.wsgi:application
