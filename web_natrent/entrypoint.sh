#!/bin/sh

sed -i 's/\r$//' entrypoint.sh

python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

exec "$@"