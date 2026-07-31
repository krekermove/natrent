import logging
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from .models import TimeTable

logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo('Europe/Moscow')

RU_MONTHS_GENITIVE = (
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
)
RU_WEEKDAYS_SHORT = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')


def format_rub(amount):
    return f'{amount:,}'.replace(',', ' ') + ' RUB'


def format_stay_date(date_value):
    weekday = RU_WEEKDAYS_SHORT[date_value.weekday()]
    month = RU_MONTHS_GENITIVE[date_value.month - 1]
    return f'{date_value.day:02d} {month} {date_value.year}, {weekday}'


def format_booking_datetime(created_at):
    local_dt = created_at.astimezone(MOSCOW_TZ)
    weekday = RU_WEEKDAYS_SHORT[local_dt.weekday()]
    month = RU_MONTHS_GENITIVE[local_dt.month - 1]
    return (
        f'{local_dt.day} {month} {local_dt.year}, {weekday} '
        f'({local_dt:%H:%M}) (UTC +03:00)'
    )


def build_booking_number(booking):
    created_local = booking.created.astimezone(MOSCOW_TZ)
    return f'{created_local:%Y%m%d}-{booking.house_id:05d}-{booking.pk:09d}'


def build_booking_email_context(booking):
    site_url = getattr(settings, 'NATRENT_SITE_URL', 'https://natrent.ru/')

    nights = (booking.enddate - booking.startdate).days

    addons = []
    if booking.addon_banya:
        addons.append('Баня')
    if booking.addon_chan:
        addons.append('Сибирский чан')

    return {
        'booking': booking,
        'addons_display': ', '.join(addons),
        'booking_number': build_booking_number(booking),
        'booking_datetime': format_booking_datetime(booking.created),
        'check_in_date': format_stay_date(booking.startdate),
        'check_out_date': format_stay_date(booking.enddate),
        'nights': nights,
        'formatted_cost': format_rub(booking.order_cost),
        'company_name': settings.NATRENT_COMPANY_NAME,
        'company_address': settings.NATRENT_ADDRESS,
        'company_phone': settings.NATRENT_PHONE,
        'company_email': settings.NATRENT_CONTACT_EMAIL,
        'site_url': site_url.rstrip('/'),
        'search_url': site_url.rstrip('/') + reverse('main:search_houses'),
    }


@shared_task(retry_backoff=True, retry_kwargs={'max_retries': 5})
def send_booking_confirmation_email(booking_id):
    try:
        booking = TimeTable.objects.get(id=booking_id)
    except:
        booking = None
    context = build_booking_email_context(booking)
    subject = f'Подтверждение бронирования № {context["booking_number"]}'
    html_body = render_to_string('main/emails/booking_confirmation.html', context)
    text_body = render_to_string('main/emails/booking_confirmation.txt', context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[booking.email],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send()
    message_to_admin = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.NATRENT_CONTACT_EMAIL],
    )
    message_to_admin.attach_alternative(html_body, 'text/html')
    message_to_admin.send()
