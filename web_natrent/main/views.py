import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Q
from django.urls import reverse

from .models import RentObject, TimeTable, DateObjectCost
from .emails import send_booking_confirmation_email

logger = logging.getLogger(__name__)


def date_transform(date):
    if not date:
        return None
    return '-'.join(reversed(date.split('.')))


def normalize_search_data(data):
    return {
        'first_date': data.get('first_date') or date_transform(data.get('firstInputDate')),
        'second_date': data.get('second_date') or date_transform(data.get('secondInputDate')),
        'guest_count': data.get('guest_count'),
        'children_under_3': data.get('children_under_3', '0'),
        'has_pet': data.get('has_pet', 'false'),
    }


MONTHS_RU = (
    '',
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
)

WEEKDAYS_RU = (
    'понедельник', 'вторник', 'среда', 'четверг',
    'пятница', 'суббота', 'воскресенье',
)


def format_date_ru(date_value):
    return f'{date_value.day} {MONTHS_RU[date_value.month]}'


def format_weekday_ru(date_value):
    return WEEKDAYS_RU[date_value.weekday()]


def parse_booking_params(data):
    first_date = data.get('first_date')
    second_date = data.get('second_date')
    guest_count = data.get('guest_count')
    children_under_3 = data.get('children_under_3', '0')
    has_pet = data.get('has_pet', 'false')

    try:
        guest_count = int(guest_count)
    except (TypeError, ValueError):
        guest_count = None

    try:
        children_under_3 = int(children_under_3)
    except (TypeError, ValueError):
        children_under_3 = 0

    has_pet_bool = str(has_pet).lower() in ('true', '1', 'on', 'yes')

    start_date = None
    end_date = None
    if first_date and second_date:
        try:
            start_date = datetime.strptime(first_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(second_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = None
            end_date = None

    return {
        'first_date': first_date,
        'second_date': second_date,
        'start_date': start_date,
        'end_date': end_date,
        'guest_count': guest_count,
        'children_under_3': children_under_3,
        'has_pet': has_pet,
        'has_pet_bool': has_pet_bool,
    }


def calculate_booking_cost(
    house,
    start_date,
    end_date,
    guest_count=1,
    children_under_3=0,
    has_pet=False,
):
    stay_nights = (end_date - start_date).days
    stay_dates = [start_date + timedelta(days=day) for day in range(stay_nights)]
    date_costs = DateObjectCost.objects.filter(
        house=house,
        date__gte=start_date,
        date__lt=end_date,
    )
    costs_by_date = {
        date_cost.date: date_cost.cost if date_cost.cost is not None else house.price
        for date_cost in date_costs
    }

    base_cost = 0
    has_all_dates_cost = stay_nights > 0
    for stay_date in stay_dates:
        night_cost = costs_by_date.get(stay_date, house.price)
        base_cost += night_cost

    extra_guests = 0
    extra_guests_cost = 0
    pet_cost = 0

    if has_all_dates_cost:
        if guest_count > 2:
            extra_guests = max(0, guest_count - children_under_3 - 2)
            extra_guests_cost = extra_guests * house.extra_guest_fee
        if has_pet:
            pet_cost = house.extra_pet_fee

    total_cost = base_cost + extra_guests_cost + pet_cost

    return {
        'base_cost': base_cost,
        'extra_guests': extra_guests,
        'extra_guests_cost': extra_guests_cost,
        'pet_cost': pet_cost,
        'total_cost': total_cost,
        'has_all_dates_cost': has_all_dates_cost,
        'stay_nights': stay_nights,
    }


def build_booking_query_string(params):
    return urlencode({
        'first_date': params['first_date'],
        'second_date': params['second_date'],
        'guest_count': params['guest_count'],
        'children_under_3': params['children_under_3'],
        'has_pet': params['has_pet'],
    })


# Create your views here.

class MainView(View):

    def get(self, request):
        return render(request, 'main/index2.html')

    def post(self, request):
        search_data = normalize_search_data(request.POST)
        first_date = search_data['first_date']
        second_date = search_data['second_date']

        context = {}
        if not first_date or not second_date:
            context['date_input_error'] = 'Вы не полностью выбрали даты проживания'
            return render(request, template_name='main/index2.html', context=context)

        if second_date <= first_date:
            context['date_input_error'] = 'Дата выезда должна быть позже даты заезда'
            return render(request, template_name='main/index2.html', context=context)

        return HttpResponseRedirect(reverse('main:search_houses'), status=307)


def popular_list(request):
    return render(request,'main/index2.html')


class SearchView(View):
    def render_search_results(self, request, data):
        first_date = data.get('first_date')
        second_date = data.get('second_date')
        guest_count = data.get('guest_count')
        children_under_3 = data.get('children_under_3', '0')
        has_pet = data.get('has_pet', 'false')

        context = {}
        if not first_date or not second_date:
            context['date_input_error'] = 'Вы не полностью выбрали даты проживания'
            return render(request, 'main/index2.html', context=context)

        try:
            guest_count = int(guest_count)
        except (TypeError, ValueError):
            guest_count = 1

        try:
            children_under_3 = int(children_under_3)
        except (TypeError, ValueError):
            children_under_3 = 0

        has_pet_bool = str(has_pet).lower() in ('true', '1', 'on', 'yes')

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
            cost_data = calculate_booking_cost(
                house,
                start_date,
                end_date,
                guest_count=guest_count,
                children_under_3=children_under_3,
                has_pet=has_pet_bool,
            )
            house.total_stay_cost = cost_data['total_cost']
            house.use_total_stay_cost = cost_data['has_all_dates_cost']
            house.stay_nights = cost_data['stay_nights']
            house.gallery_images = [
                image_field for image_field in [house.img1, house.img2, house.img3, house.img4] if image_field
            ]
            print(house.total_stay_cost, house.use_total_stay_cost, house.stay_nights)
        
        context['free_houses'] = free_houses
        context['first_date'] = first_date
        context['second_date'] = second_date
        context['guest_count'] = guest_count
        context['children_under_3'] = children_under_3
        context['has_pet'] = has_pet
        print(context)
        return render(request, 'main/search_houses.html', context=context)

    def get(self, request):
        return self.render_search_results(request, request.GET)

    def post(self, request):
        return self.render_search_results(request, normalize_search_data(request.POST))


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
    def get_booking_context(self, house, params):
        start_date = params['start_date']
        end_date = params['end_date']
        guest_count = params['guest_count']
        children_under_3 = params['children_under_3']
        has_pet_bool = params['has_pet_bool']

        cost_data = calculate_booking_cost(
            house,
            start_date,
            end_date,
            guest_count=guest_count,
            children_under_3=children_under_3,
            has_pet=has_pet_bool,
        )

        house.gallery_images = [
            image_field for image_field in [house.img1, house.img2, house.img3, house.img4] if image_field
        ]

        return {
            'house': house,
            'first_date': params['first_date'],
            'second_date': params['second_date'],
            'start_date': start_date,
            'end_date': end_date,
            'guest_count': guest_count,
            'children_under_3': children_under_3,
            'has_pet': params['has_pet'],
            'has_pet_bool': has_pet_bool,
            'cost_data': cost_data,
            'check_in_date_display': format_date_ru(start_date),
            'check_out_date_display': format_date_ru(end_date),
            'check_in_weekday': format_weekday_ru(start_date),
            'check_out_weekday': format_weekday_ru(end_date),
            'date_range_display': f'{format_date_ru(start_date)} — {format_date_ru(end_date)}',
        }

    def validate_booking_params(self, house, params):
        start_date = params['start_date']
        end_date = params['end_date']
        guest_count = params['guest_count']

        if not params['first_date'] or not params['second_date']:
            return 'Вы не полностью выбрали даты проживания.'

        if start_date is None or end_date is None:
            return 'Некорректный формат дат.'

        if end_date <= start_date:
            return 'Дата выезда должна быть позже даты заезда.'

        if guest_count is None or guest_count < 1:
            return 'Укажите количество гостей.'

        if guest_count > house.max_guests:
            return 'Количество гостей превышает максимальное для этого дома.'

        is_busy = TimeTable.objects.filter(
            Q(startdate__lt=end_date),
            Q(enddate__gt=start_date),
            status=True,
            house=house,
        ).exists()
        if is_busy:
            return 'На выбранные даты этот дом уже забронирован.'

        cost_data = calculate_booking_cost(
            house,
            start_date,
            end_date,
            guest_count=guest_count,
            children_under_3=params['children_under_3'],
            has_pet=params['has_pet_bool'],
        )
        if not cost_data['has_all_dates_cost']:
            return 'Не удалось рассчитать стоимость проживания на выбранные даты.'

        return None

    def render_booking_page(self, request, house, params, form_data=None):
        context = self.get_booking_context(house, params)
        if form_data:
            context['form_data'] = form_data
        return render(request, 'main/book_house.html', context)

    def redirect_to_search(self, params):
        search_url = reverse('main:search_houses')
        if params['first_date'] and params['second_date'] and params['guest_count']:
            return redirect(f'{search_url}?{build_booking_query_string(params)}')
        return redirect(search_url)

    def get(self, request, house_id):
        messages.error(request, 'Для бронирования выберите дом на странице поиска.')
        return redirect(reverse('main:search_houses'))

    def post(self, request, house_id):
        house = get_object_or_404(RentObject, pk=house_id)
        params = parse_booking_params(request.POST)
        form_action = request.POST.get('form_action', 'show')

        if form_action == 'show':
            error = self.validate_booking_params(house, params)
            if error:
                messages.error(request, error)
                return self.redirect_to_search(params)
            return self.render_booking_page(request, house, params)

        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        comment = request.POST.get('comment', '').strip()
        form_data = {
            'name': name,
            'phone': phone,
            'email': email,
            'comment': comment,
            'personal_data_consent': bool(request.POST.get('personal_data_consent')),
        }

        if not request.POST.get('personal_data_consent'):
            messages.error(request, 'Необходимо дать согласие на обработку персональных данных.')
            return self.render_booking_page(request, house, params, form_data)

        error = self.validate_booking_params(house, params)
        if error:
            messages.error(request, error)
            return self.render_booking_page(request, house, params, form_data)

        if not all([name, phone, email]):
            messages.error(request, 'Заполните обязательные поля для бронирования.')
            return self.render_booking_page(request, house, params, form_data)

        cost_data = calculate_booking_cost(
            house,
            params['start_date'],
            params['end_date'],
            guest_count=params['guest_count'],
            children_under_3=params['children_under_3'],
            has_pet=params['has_pet_bool'],
        )

        try:
            booking = TimeTable(
                name=name,
                phone=phone,
                email=email,
                house=house,
                startdate=params['start_date'],
                enddate=params['end_date'],
                guests_amount=params['guest_count'],
                children_under_3=params['children_under_3'],
                has_pet=params['has_pet_bool'],
                comment=comment,
                order_cost=cost_data['total_cost'],
            )
            booking.save()
        except ValueError as error:
            messages.error(request, str(error))
            return self.render_booking_page(request, house, params, form_data)

        try:
            send_booking_confirmation_email(booking, request)
        except Exception:
            logger.exception(
                'Не удалось отправить письмо с подтверждением бронирования %s',
                booking.pk,
            )

        messages.success(request, f'Заявка на бронирование "{house.name}" отправлена.')
        return self.redirect_to_search(params)