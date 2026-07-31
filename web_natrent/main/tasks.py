import logging

from celery import shared_task
from datetime import date

from .models import TimeTable

logger = logging.getLogger(__name__)


@shared_task
def scheduled_task():
    today = date.today()
    try:
        books = TimeTable.objects.filter(enddate__lte=today).exclude(status=False)
        for book in books:
            book.status = False
            book.save()
            logger.info('Статус брони %s успешно изменен на "Истекла"', book.id)
    except:
        return None
    return None