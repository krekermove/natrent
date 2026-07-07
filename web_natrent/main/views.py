import json
import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Q
from django.urls import reverse

from .models import RentObject, TimeTable, DateObjectCost, Feedback
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
        'addon_banya': data.get('addon_banya'),
        'addon_chan': data.get('addon_chan'),
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

# Стоимость дополнительных услуг (баня и сибирский чан).
# Должна совпадать с ценами в шаблоне страницы объекта.
BANYA_PRICE = 6000
CHAN_PRICE = 6000
BANYA_CHAN_COMBO_PRICE = 11000  # баня + чан вместе на 3 часа — выгоднее


def addons_cost(addon_banya, addon_chan, id):
    """Стоимость и подпись выбранных доп. услуг (баня/чан).
    Вместе они дешевле, чем по отдельности."""
    if id == 1:
        BANYA_PRICE = 6000
    else:
        BANYA_PRICE = 5000
    if addon_banya and addon_chan:
        return BANYA_CHAN_COMBO_PRICE, 'Баня + чан · 3 часа'
    if addon_banya:
        return BANYA_PRICE, 'Баня'
    if addon_chan:
        return CHAN_PRICE, 'Сибирский чан'
    return 0, ''


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

    addon_banya = bool(data.get('addon_banya'))
    addon_chan = bool(data.get('addon_chan'))

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
        'addon_banya': addon_banya,
        'addon_chan': addon_chan,
    }


def calculate_booking_cost(
    house,
    start_date,
    end_date,
    guest_count=1,
    children_under_3=0,
    has_pet=False,
    addon_banya=False,
    addon_chan=False,
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
    addon_cost = 0
    addon_label = ''

    if has_all_dates_cost:
        if guest_count > 2:
            extra_guests = max(0, guest_count - children_under_3 - 2)
            extra_guests_cost = extra_guests * house.extra_guest_fee * stay_nights
        if has_pet:
            pet_cost = house.extra_pet_fee * stay_nights
        addon_cost, addon_label = addons_cost(addon_banya, addon_chan, house.id)

    total_cost = base_cost + extra_guests_cost + pet_cost + addon_cost

    return {
        'base_cost': base_cost,
        'extra_guests': extra_guests,
        'extra_guests_cost': extra_guests_cost,
        'pet_cost': pet_cost,
        'addon_banya': addon_banya,
        'addon_chan': addon_chan,
        'addon_cost': addon_cost,
        'addon_label': addon_label,
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


def build_booking_context(house, params):
    """Контекст для страницы оформления брони (book_object.html)."""
    start_date = params['start_date']
    end_date = params['end_date']
    guest_count = params['guest_count']
    children_under_3 = params['children_under_3']
    has_pet_bool = params['has_pet_bool']
    addon_banya = params['addon_banya']
    addon_chan = params['addon_chan']

    cost_data = calculate_booking_cost(
        house,
        start_date,
        end_date,
        guest_count=guest_count,
        children_under_3=children_under_3,
        has_pet=has_pet_bool,
        addon_banya=addon_banya,
        addon_chan=addon_chan,
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
        'addon_banya': addon_banya,
        'addon_chan': addon_chan,
        'cost_data': cost_data,
        'check_in_date_display': format_date_ru(start_date),
        'check_out_date_display': format_date_ru(end_date),
        'check_in_weekday': format_weekday_ru(start_date),
        'check_out_weekday': format_weekday_ru(end_date),
        'date_range_display': f'{format_date_ru(start_date)} — {format_date_ru(end_date)}',
    }


def validate_booking_params(house, params):
    """Проверяет выбранные пользователем параметры брони.
    Возвращает текст ошибки или None, если всё корректно."""
    start_date = params['start_date']
    end_date = params['end_date']
    guest_count = params['guest_count']

    if not params['first_date'] or not params['second_date']:
        return 'Вы не полностью выбрали даты проживания.'

    if start_date is None or end_date is None:
        return 'Некорректный формат дат.'

    if end_date <= start_date:
        return 'Дата выезда должна быть позже даты заезда.'

    nights = (end_date - start_date).days
    if nights < house.min_nights:
        n = house.min_nights
        a, b = n % 100, n % 10
        if a > 10 and a < 20:
            word = 'ночей'
        elif b == 1:
            word = 'ночь'
        elif 2 <= b <= 4:
            word = 'ночи'
        else:
            word = 'ночей'
        return f'Минимальный срок бронирования — {n} {word}.'

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


# Create your views here.

class MainView(View):

    def _load_houses(self):
        houses = list(RentObject.objects.all())
        for house in houses:
            house.gallery_images = [
                img for img in [house.img1, house.img2, house.img3, house.img4] if img
            ]
        return houses

    def get(self, request):
        return render(request, 'main/index.html', {'houses': self._load_houses()})

    def post(self, request):
        search_data = normalize_search_data(request.POST)
        first_date = search_data['first_date']
        second_date = search_data['second_date']

        base_context = {}

        if not first_date or not second_date:
            base_context['date_input_error'] = 'Вы не полностью выбрали даты проживания'
            base_context['houses'] = self._load_houses()
            return render(request, 'main/index.html', context=base_context)

        if second_date <= first_date:
            base_context['date_input_error'] = 'Дата выезда должна быть позже даты заезда'
            base_context['houses'] = self._load_houses()
            return render(request, 'main/index.html', context=base_context)

        try:
            guest_count = int(search_data.get('guest_count') or 1)
        except (TypeError, ValueError):
            guest_count = 1
        try:
            children_under_3 = int(search_data.get('children_under_3') or 0)
        except (TypeError, ValueError):
            children_under_3 = 0
        has_pet = search_data.get('has_pet', 'false')
        has_pet_bool = str(has_pet).lower() in ('true', '1', 'on', 'yes')

        start_date = datetime.strptime(first_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(second_date, '%Y-%m-%d').date()
        nights = (end_date - start_date).days

        busy_ids = TimeTable.objects.filter(
            Q(startdate__lt=second_date),
            Q(enddate__gt=first_date),
            status=True,
        ).values_list('house_id', flat=True)

        free_houses_qs = RentObject.objects.filter(
            max_guests__gte=guest_count
        ).exclude(id__in=busy_ids)

        if has_pet_bool:
            free_houses_qs = free_houses_qs.filter(pets_allowed=True)

        free_houses_qs = free_houses_qs.filter(min_nights__lte=nights)

        free_houses = list(free_houses_qs)

        for house in free_houses:
            cost_data = calculate_booking_cost(
                house, start_date, end_date,
                guest_count=guest_count,
                children_under_3=children_under_3,
                has_pet=has_pet_bool,
            )
            house.total_stay_cost = cost_data['total_cost']
            house.use_total_stay_cost = cost_data['has_all_dates_cost']
            house.stay_nights = cost_data['stay_nights']
            house.gallery_images = [
                img for img in [house.img1, house.img2, house.img3, house.img4] if img
            ]

        return render(request, 'main/index.html', {
            'houses': free_houses,
            'first_date': first_date,
            'second_date': second_date,
            'guest_count': guest_count,
            'children_under_3': children_under_3,
            'has_pet': has_pet,
            'search_applied': True,
        })


def popular_list(request):
    return render(request,'main/index.html')


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
            return render(request, 'main/index.html', context=context)

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
            return render(request, 'main/index.html', context=context)

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

        if has_pet_bool:
            free_houses = free_houses.filter(pets_allowed=True)

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
    @staticmethod
    def _load_houses(house_id):
        houses = list(RentObject.objects.exclude(id=house_id))
        for house in houses:
            house.gallery_images = [
                img for img in [house.img1, house.img2, house.img3, house.img4] if img
            ]
        return houses

    def get(self, request, house_id):
        house = get_object_or_404(RentObject, pk=house_id)
        slug = ''
        if house_id == 1:
            slug = 'detail_house_annolovo'
        elif house_id == 2:
            slug = 'detail_house_fedorov'
        elif house_id == 3:
            slug = 'detail_novoizm'


        date_costs = {
            date_cost.date.strftime('%Y-%m-%d'): date_cost.cost
            for date_cost in DateObjectCost.objects.filter(house=house)
            if date_cost.cost is not None
        }

        houses = HouseDetailView._load_houses(house_id)

        return render(request, f'main/{slug}.html', {
            'house': house,
            'yandex_maps_api_key': settings.YANDEX_MAPS_API_KEY,
            'date_costs_json': json.dumps(date_costs),
            'houses': houses
        })

    def post(self, request, house_id):
        """Отправка формы бронирования со страницы объекта.
        Переносит выбранные пользователем данные на страницу оформления брони."""
        house = get_object_or_404(RentObject, pk=house_id)
        params = parse_booking_params(normalize_search_data(request.POST))

        error = validate_booking_params(house, params)
        if error:
            messages.error(request, error)
            return redirect(reverse('main:house_detail', args=[house_id]))

        # Перенаправляем на оформление брони, передавая выбранные данные
        # в теле POST-запроса. Код 307 заставляет браузер повторить запрос
        # тем же методом (POST) и с тем же телом на указанный viewname.
        response = HttpResponseRedirect(reverse('main:book_house', args=[house_id]))
        response.status_code = 307
        return response


class FeedbackView(View):
    """Приём сообщений из формы обратной связи (.form-col) на главной странице."""

    def get(self, request):
        return redirect(f"{reverse('main:main_page')}#contact")

    def post(self, request):
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not phone:
            messages.error(request, 'Укажите имя и телефон, чтобы мы могли с вами связаться.')
        else:
            Feedback.objects.create(name=name, phone=phone, message=message)
            messages.success(request, 'Спасибо! Мы получили ваше сообщение и скоро свяжемся с вами.')

        return redirect(f"{reverse('main:main_page')}#contact")


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
    def render_booking_page(self, request, house, params, form_data=None):
        context = build_booking_context(house, params)
        if form_data:
            context['form_data'] = form_data
        return render(request, 'main/book_object.html', context)

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
        # normalize_search_data приводит поля разных форм к единому виду
        # (в т.ч. firstInputDate -> first_date), чтобы корректно принять
        # данные, переданные 307-редиректом со страницы объекта.
        params = parse_booking_params(normalize_search_data(request.POST))
        form_action = request.POST.get('form_action', 'show')

        if form_action == 'show':
            error = validate_booking_params(house, params)
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

        error = validate_booking_params(house, params)
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
            addon_banya=params['addon_banya'],
            addon_chan=params['addon_chan'],
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
                addon_banya=params['addon_banya'],
                addon_chan=params['addon_chan'],
                comment=comment,
                order_cost=cost_data['total_cost'],
            )
            booking.save()
        except ValueError as error:
            messages.error(request, str(error))
            return self.render_booking_page(request, house, params, form_data)

        try:
            send_booking_confirmation_email.delay(booking.id)
        except Exception:
            logger.exception(
                'Не удалось отправить письмо с подтверждением бронирования %s',
                booking.pk,
            )

        messages.success(
            request,
            f'Заявка на бронирование «{house.name}» отправлена. '
            f'Мы свяжемся с вами для подтверждения брони.',
        )
        # Не перенаправляем — показываем подтверждение на этой же странице.
        context = build_booking_context(house, params)
        context['booking_success'] = True
        return render(request, 'main/book_object.html', context)