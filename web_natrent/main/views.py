import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Q
from django.urls import reverse

from .models import RentObject, TimeTable, DateObjectCost
from .emails import send_booking_confirmation_email

logger = logging.getLogger(__name__)


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
        guest_count = request.POST.get('guest_count')
        guests_amount = request.POST.get('guestInputValue')
        children_under_3 = request.POST.get('children_under_3', '0')
        has_pet = request.POST.get('has_pet', 'false')

        context = {}
        if not first_date or not second_date:
            context['date_input_error'] = 'Вы не полностью выбрали даты проживания'
            return render(request, template_name='main/index2.html', context=context)

        try:
            guest_count = int(guest_count)
        except (TypeError, ValueError):
            try:
                guest_count = int(guests_amount)
            except (TypeError, ValueError):
                guest_count = 1

        try:
            guests_amount = int(guests_amount)
        except (TypeError, ValueError):
            guests_amount = guest_count

        try:
            children_under_3 = int(children_under_3)
        except (TypeError, ValueError):
            children_under_3 = 0

        if second_date <= first_date:
            context['date_input_error'] = 'Дата выезда должна быть позже даты заезда'
            return render(request, template_name='main/index2.html', context=context)

        query_string = urlencode({
            'first_date': first_date,
            'second_date': second_date,
            'guest_count': guest_count,
            'guests_amount': guests_amount,
            'children_under_3': children_under_3,
            'has_pet': has_pet,
        })
        search_url = reverse('main:search_houses')
        return redirect(f'{search_url}?{query_string}')


def popular_list(request):
    return render(request,'main/index2.html')


class SearchView(View):
    def calculate_house_cost(self, house, start_date, end_date):
        stay_nights = (end_date - start_date).days
        stay_dates = [start_date + timedelta(days=day) for day in range(stay_nights)]
        date_costs = DateObjectCost.objects.filter(
            house=house,
            date__gte=start_date,
            date__lt=end_date,
        )
        costs_by_date = {date_cost.date: date_cost.cost for date_cost in date_costs}

        total_stay_cost = 0
        has_all_dates_cost = stay_nights > 0
        for stay_date in stay_dates:
            night_cost = costs_by_date.get(stay_date)
            if night_cost is None:
                has_all_dates_cost = False
                break
            total_stay_cost += night_cost

        return total_stay_cost, has_all_dates_cost, stay_nights

    def get(self, request):
        first_date = request.GET.get('first_date')
        second_date = request.GET.get('second_date')
        guest_count = request.GET.get('guest_count')
        guests_amount = request.GET.get('guests_amount')
        children_under_3 = request.GET.get('children_under_3', '0')
        has_pet = request.GET.get('has_pet', 'false')

        context = {}
        if not first_date or not second_date:
            context['date_input_error'] = 'Вы не полностью выбрали даты проживания'
            return render(request, 'main/index2.html', context=context)

        try:
            guest_count = int(guest_count)
        except (TypeError, ValueError):
            guest_count = 1

        try:
            guests_amount = int(guests_amount)
        except (TypeError, ValueError):
            guests_amount = guest_count

        try:
            children_under_3 = int(children_under_3)
        except (TypeError, ValueError):
            children_under_3 = 0

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
        free_houses = list(free_houses)

        for house in free_houses:
            total_stay_cost, has_all_dates_cost, stay_nights = self.calculate_house_cost(
                house,
                start_date,
                end_date,
            )
            house.total_stay_cost = total_stay_cost
            house.use_total_stay_cost = has_all_dates_cost
            house.stay_nights = stay_nights
            house.gallery_images = [
                image_field for image_field in [house.img1, house.img2, house.img3, house.img4] if image_field
            ]
        
        context['free_houses'] = free_houses
        context['first_date'] = first_date
        context['second_date'] = second_date
        context['guest_count'] = guest_count
        context['guests_amount'] = guests_amount
        context['children_under_3'] = children_under_3
        context['has_pet'] = has_pet

        return render(request, 'main/search_houses.html', context=context)


class HouseDetailView(View):
    def get(self, request, house_id):
        house = get_object_or_404(RentObject, pk=house_id)
        house.gallery_images = [image_field for image_field in [house.img1, house.img2, house.img3, house.img4] if image_field]
        return render(request, 'main/house_detail.html', {'house': house})


class PersonalDataConsentView(View):
    def get(self, request):
        return render(request, 'main/legal/personal_data_consent.html')


class UserAgreementView(View):
    def get(self, request):
        return render(request, 'main/legal/user_agreement.html')


class PrivacyPolicyView(View):
    def get(self, request):
        return render(request, 'main/legal/privacy_policy.html')


class BookHouseView(View):
    def post(self, request):
        house_id = request.POST.get('house_id')
        first_date = request.POST.get('first_date')
        second_date = request.POST.get('second_date')
        guest_count = request.POST.get('guest_count')
        guests_amount = request.POST.get('guests_amount')
        children_under_3 = request.POST.get('children_under_3', '0')
        has_pet = request.POST.get('has_pet', 'false')
        order_cost = request.POST.get('order_cost')
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        comment = request.POST.get('comment', '').strip()

        search_url = reverse('main:search_houses')
        query_string = urlencode({
            'first_date': first_date,
            'second_date': second_date,
            'guest_count': guest_count,
        })

        house = get_object_or_404(RentObject, pk=house_id)

        if not request.POST.get('personal_data_consent'):
            messages.error(request, 'Необходимо дать согласие на обработку персональных данных.')
            return redirect(f'{search_url}?{query_string}')

        if not all([name, phone, email, first_date, second_date, guest_count, order_cost]):
            messages.error(request, 'Заполните обязательные поля для бронирования.')
            return redirect(f'{search_url}?{query_string}')

        try:
            start_date = datetime.strptime(first_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(second_date, "%Y-%m-%d").date()
            guests_amount = int(guests_amount or guest_count)
            children_under_3 = int(children_under_3)
            has_pet = str(has_pet).lower() in ('true', '1', 'on', 'yes')
            booking_cost = int(order_cost)
        except (TypeError, ValueError):
            messages.error(request, 'Некорректные данные формы бронирования.')
            return redirect(f'{search_url}?{query_string}')

        try:
            booking = TimeTable(
                name=name,
                phone=phone,
                email=email,
                house=house,
                startdate=start_date,
                enddate=end_date,
                guests_amount=guests_amount,
                children_under_3=children_under_3,
                has_pet=has_pet,
                comment=comment,
                order_cost=booking_cost,
            )
            booking.save()
        except ValueError as error:
            messages.error(request, str(error))
            return redirect(f'{search_url}?{query_string}')

        try:
            send_booking_confirmation_email(booking, request)
        except Exception:
            logger.exception(
                'Не удалось отправить письмо с подтверждением бронирования %s',
                booking.pk,
            )

        messages.success(request, f'Заявка на бронирование "{house.name}" отправлена.')
        return redirect(f'{search_url}?{query_string}')