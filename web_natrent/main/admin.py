import datetime

from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path

from .forms import BookingForm, CostForm
from .models import TimeTable, RentObject, DateObjectCost


@admin.register(TimeTable)
class TimeTableAdmin(admin.ModelAdmin):
    list_display = ('phone', 'house', 'startdate', 'enddate', 'status')

    change_list_template = 'admin/timetable_changelist.html'

    recently_month = -1
    recently_year = -1

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('timetable_calendar/', self.admin_site.admin_view(self.timetable_calendar_view), name='timetable_calendar'),
        ]
        return my_urls + urls

    def booked_days_counter(self, house_type):
        booked_days = []
        try:
            intervals = TimeTable.objects.filter(house=house_type)
            for interval in intervals:
                start_date = interval.startdate
                booked_days.append(start_date.strftime('%Y-%m-%d'))
                while start_date < interval.enddate:
                    start_date += datetime.timedelta(days=1)
                    booked_days.append(start_date.strftime('%Y-%m-%d'))
            return booked_days
        except:
            return booked_days

    def dates_with_cost(self, context, house_type):
        dates = DateObjectCost.objects.filter(house=house_type)
        context['dates_object_cost'][f"{house_type}"] = {}
        for date in dates:
            context['dates_object_cost'][f"{house_type}"][f"{date.date}"] = date.cost

    def context_for_timetable_page(self, request):
        objects = RentObject.objects.all()
        context = dict(
            self.admin_site.each_context(request),
        )
        context['booked_days'] = {}
        context['dates_object_cost'] = {}
        for el in objects:
            context[f'booked_days'][f"{el.id}"] = self.booked_days_counter(el.id)
            self.dates_with_cost(context, el.id)
        context['objects'] = objects
        context['length'] = len(objects)
        context['form'] = BookingForm()
        context['formCost'] = CostForm()
        context['month'] = self.recently_month
        context['year'] = self.recently_year
        return context

    def timetable_calendar_view(self, request):
        if request.method == 'GET':
            context = self.context_for_timetable_page(request)
            self.recently_month = -1
            self.recently_year = -1
            return render(request, "admin/timetable_calendar.html", context=context)
        elif request.method == 'POST':
            tmp_month = request.POST.get('month')
            tmp_year = request.POST.get('year')
            if tmp_month: self.recently_month = tmp_month
            if tmp_year: self.recently_year = tmp_year
            input_date = request.POST.get('date')
            if input_date:
                form = CostForm(request.POST)
                house = request.POST.get('house1')
                date = datetime.datetime.strptime(input_date, "%Y-%m-%d").date()
                try:
                    cost_obj = DateObjectCost.objects.get(date=date, house=house)
                except:
                    cost_obj = None
                if form.is_valid():
                    if cost_obj:
                        cost_obj.cost = form.cleaned_data.get('cost')
                        cost_obj.save()
                    else:
                        instance = form.save(commit=False)
                        instance.date = date
                        instance.house = RentObject.objects.get(id=house)
                        instance.cost = form.cleaned_data.get('cost')
                        instance.save()
                    return redirect('admin:timetable_calendar')
                context = self.context_for_timetable_page(request)
                return render(request, "admin/timetable_calendar.html", context=context)
            else:
                form = BookingForm(request.POST)
                print("1")
                if form.is_valid():
                    instance = form.save(commit=False)
                    instance.name = form.cleaned_data.get('name')
                    instance.phone = form.cleaned_data.get('phone')
                    instance.house = form.cleaned_data.get('house')
                    instance.startdate = form.cleaned_data.get('startdate')
                    instance.enddate = form.cleaned_data.get('enddate')
                    instance.guests_amount = form.cleaned_data.get('guests_amount')
                    instance.comment = form.cleaned_data.get('comment')
                    instance.order_cost = form.cleaned_data.get('order_cost')
                    instance.save()
                    print("1")
                    return redirect('admin:timetable_calendar')
                context = self.context_for_timetable_page(request)
                return render(request, "admin/timetable_calendar.html", context=context)


@admin.register(RentObject)
class RentObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_guests', 'price')


@admin.register(DateObjectCost)
class DateObjectCostAdmin(admin.ModelAdmin):
    list_display = ('date', 'house', 'cost')
