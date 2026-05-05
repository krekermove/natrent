from urllib.parse import urlencode
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.views import View
from django.db.models import Q
from django.urls import reverse

from .models import RentObject, TimeTable, DateObjectCost


# Create your views here.

class MainView(View):
    def date_transform(self, date):
        if not date:
            return None
        return '-'.join(reversed(date.split('.')))

    def get(self, request):
        return render(request, 'main/index2.html')

    def post(self, request):
        first_date = self.date_transform(request.POST.get('firstInputDate'))
        second_date = self.date_transform(request.POST.get('secondInputDate'))
        guest_count = request.POST.get('guestInputValue')

        context = {}
        if not first_date or not second_date:
            context['date_input_error'] = 'Вы не полностью выбрали даты проживания'
            return render(request, template_name='main/index2.html', context=context)

        try:
            guest_count = int(guest_count)
        except (TypeError, ValueError):
            guest_count = 1

        if second_date <= first_date:
            context['date_input_error'] = 'Дата выезда должна быть позже даты заезда'
            return render(request, template_name='main/index2.html', context=context)

        query_string = urlencode({
            'first_date': first_date,
            'second_date': second_date,
            'guest_count': guest_count,
        })
        search_url = reverse('main:search_houses')
        return redirect(f'{search_url}?{query_string}')


def popular_list(request):
    return render(request,'main/index2.html')


class SearchView(View):
    def get(self, request):
        first_date = request.GET.get('first_date')
        second_date = request.GET.get('second_date')
        guest_count = request.GET.get('guest_count')

        context = {}
        if not first_date or not second_date:
            context['date_input_error'] = 'Вы не полностью выбрали даты проживания'
            return render(request, 'main/index2.html', context=context)

        try:
            guest_count = int(guest_count)
        except (TypeError, ValueError):
            guest_count = 1

        if second_date <= first_date:
            context['date_input_error'] = 'Дата выезда должна быть позже даты заезда'
            return render(request, 'main/index2.html', context=context)

        busy_houses_ids = TimeTable.objects.filter(
            Q(startdate__lt=second_date),
            Q(enddate__gt=first_date),
            status=True,
        ).values_list('house_id', flat=True)

        free_houses = RentObject.objects.filter(
            max_guests__gte=guest_count
        ).exclude(
            id__in=busy_houses_ids
        )

        start_date = datetime.strptime(first_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(second_date, "%Y-%m-%d").date()
        stay_nights = (end_date - start_date).days
        stay_dates = [start_date + timedelta(days=day) for day in range(stay_nights)]

        free_houses = list(free_houses)
        house_ids = [house.id for house in free_houses]
        date_costs = DateObjectCost.objects.filter(
            house_id__in=house_ids,
            date__gte=start_date,
            date__lt=end_date,
        )

        costs_by_house_and_date = {
            (date_cost.house_id, date_cost.date): date_cost.cost
            for date_cost in date_costs
        }

        for house in free_houses:
            total_stay_cost = 0
            has_all_dates_cost = True
            for stay_date in stay_dates:
                night_cost = costs_by_house_and_date.get((house.id, stay_date))
                if night_cost is None:
                    has_all_dates_cost = False
                    break
                total_stay_cost += night_cost
            house.total_stay_cost = total_stay_cost
            house.use_total_stay_cost = has_all_dates_cost and stay_nights > 0
            house.stay_nights = stay_nights
            house.gallery_images = [
                image_field for image_field in [house.img1, house.img2, house.img3, house.img4] if image_field
            ]
        
        print(free_houses[0].stay_nights)
        context['free_houses'] = free_houses
        context['first_date'] = first_date
        context['second_date'] = second_date
        context['guest_count'] = guest_count

        return render(request, 'main/search_houses.html', context=context)