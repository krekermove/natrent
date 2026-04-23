#!/bin/sh

sed -i 's/\r$//' entrypoint.sh

python manage.py collectstatic
python manage.py makemigrations
python manage.py migrate

exec "$@"