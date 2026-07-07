import datetime
import json

from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path

from .models import TimeTable, RentObject, DateObjectCost, Feedback

CLOSED_BY_ADMIN_NAME = 'Закрыто администратором'


@admin.register(TimeTable)
class TimeTableAdmin(admin.ModelAdmin):
    list_display = ('phone', 'house', 'startdate', 'enddate', 'status', 'guests_amount', 'has_pet', 'addon_banya', 'addon_chan', 'created')

    change_list_template = 'admin/timetable_changelist.html'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('timetable_calendar/', self.admin_site.admin_view(self.timetable_calendar_view), name='timetable_calendar'),
        ]
        return my_urls + urls

    def booked_days_counter(self, house_id):
        """Все занятые даты дома (включая дату выезда) в формате YYYY-MM-DD."""
        booked_days = []
        for interval in TimeTable.objects.filter(house=house_id):
            day = interval.startdate
            while day <= interval.enddate:
                booked_days.append(day.strftime('%Y-%m-%d'))
                day += datetime.timedelta(days=1)
        return booked_days

    def dates_with_cost(self, house_id):
        return {
            date_cost.date.strftime('%Y-%m-%d'): date_cost.cost
            for date_cost in DateObjectCost.objects.filter(house=house_id)
        }

    def close_dates(self, house, start, end):
        """Закрывает свободные даты из [start, end], разбивая диапазон на
        отрезки вокруг уже существующих броней. Возвращает текст ошибки или None."""
        closed = set()
        for interval in TimeTable.objects.filter(house=house):
            day = interval.startdate
            while day <= interval.enddate:
                closed.add(day)
                day += datetime.timedelta(days=1)

        segments = []
        segment_start = None
        day = start
        while day <= end:
            if day in closed:
                if segment_start:
                    segments.append((segment_start, day - datetime.timedelta(days=1)))
                    segment_start = None
            elif segment_start is None:
                segment_start = day
            day += datetime.timedelta(days=1)
        if segment_start:
            segments.append((segment_start, end))

        if not segments:
            return 'Все выбранные даты уже закрыты.'

        for segment_start, segment_end in segments:
            closure = TimeTable(
                name=CLOSED_BY_ADMIN_NAME,
                phone='—',
                email='admin@natrent.ru',
                house=house,
                startdate=segment_start,
                enddate=segment_end,
                guests_amount=1,
                comment='Даты закрыты через календарь в админке',
                order_cost=0,
            )
            try:
                closure.save()
            except ValueError as error:
                return str(error)
        return None

    def open_dates(self, house, start, end):
        """Удаляет все брони и закрытия дома, пересекающиеся с [start, end]."""
        TimeTable.objects.filter(house=house, startdate__lte=end, enddate__gte=start).delete()
        return None

    def set_cost(self, house, start, end, cost):
        """Устанавливает стоимость проживания для каждой даты из [start, end]."""
        day = start
        while day <= end:
            DateObjectCost.objects.update_or_create(date=day, house=house, defaults={'cost': cost})
            day += datetime.timedelta(days=1)
        return None

    def calendar_action(self, request):
        try:
            data = json.loads(request.body)
            action = data.get('action')
            house = RentObject.objects.get(id=data.get('house'))
            start = datetime.date.fromisoformat(data.get('start'))
            end = datetime.date.fromisoformat(data.get('end'))
        except (json.JSONDecodeError, RentObject.DoesNotExist, TypeError, ValueError):
            return JsonResponse({'error': 'Некорректные данные запроса.'}, status=400)
        if end < start:
            start, end = end, start

        if action == 'close':
            error = self.close_dates(house, start, end)
        elif action == 'open':
            error = self.open_dates(house, start, end)
        elif action == 'set_cost':
            try:
                cost = int(data.get('cost'))
            except (TypeError, ValueError):
                cost = -1
            if cost < 0:
                return JsonResponse({'error': 'Укажите корректную стоимость.'}, status=400)
            error = self.set_cost(house, start, end, cost)
        else:
            return JsonResponse({'error': 'Неизвестное действие.'}, status=400)

        if error:
            return JsonResponse({'error': error}, status=400)
        return JsonResponse({
            'booked_days': self.booked_days_counter(house.id),
            'dates_object_cost': self.dates_with_cost(house.id),
        })

    def timetable_calendar_view(self, request):
        if request.method == 'POST':
            return self.calendar_action(request)
        objects = RentObject.objects.all()
        context = dict(
            self.admin_site.each_context(request),
            objects=objects,
            booked_days_json=json.dumps({str(el.id): self.booked_days_counter(el.id) for el in objects}),
            dates_object_cost_json=json.dumps({str(el.id): self.dates_with_cost(el.id) for el in objects}),
        )
        return render(request, "admin/timetable_calendar.html", context=context)


@admin.register(RentObject)
class RentObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'max_guests', 'price', 'pets_allowed', 'min_nights')


@admin.register(DateObjectCost)
class DateObjectCostAdmin(admin.ModelAdmin):
    list_display = ('date', 'house', 'cost')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'created', 'is_processed')
    list_filter = ('is_processed', 'created')
    list_editable = ('is_processed',)
    search_fields = ('name', 'phone', 'message')
    readonly_fields = ('name', 'phone', 'message', 'created')
    date_hierarchy = 'created'
