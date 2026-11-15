#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py createcachetable
python manage.py collectstatic --noinput

# Public demo: load the demo data set on first start (no-op when data exists).
case "${DEMO_MODE:-False}" in
  1|true|True|yes) python manage.py seed_demo ;;
esac

exec "$@"
