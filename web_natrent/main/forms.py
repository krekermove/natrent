from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import TimeTable, RentObject, DateObjectCost


class CostForm(forms.ModelForm):
    cost = forms.IntegerField(
        label=_("Стоимость"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Введите стоимость'})
    )

    class Meta:
        model = DateObjectCost
        fields = ['cost',]


class BookingForm(forms.ModelForm):
    name = forms.CharField(
        label=_("Имя"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите имя клиента'})
    )
    phone = forms.CharField(
        label=_("Номер телефона"),
        error_messages={
            "min_length": _("Введите номер телефона в формате +7 (___) ___-__-__")
        },
        help_text="",
        min_length=18,
        max_length=18,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (___) ___-__-__'})
    )
    email = forms.EmailField(
        label=_("Электронная почта"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.ru'})
    )
    # house = forms.ChoiceField(
    #     label=_("Дом"),
    #     choices=RentObject.objects.all(),
    # )
    startdate = forms.DateField(
        label=_("Дата заезда"),
        widget=forms.DateInput(attrs={'class': 'date-input form-control', 'placeholder': 'Выберите дату заезда'})
    )
    enddate = forms.DateField(
        label=_("Дата выезда"),
        widget=forms.DateInput(attrs={'class': 'date-input form-control', 'placeholder': 'Выберите дату выезда'})
    )
    guests_amount = forms.IntegerField(
        label=_("Количество гостей"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Введите количество гостей'})
    )
    comment = forms.CharField(
        label=_("Комментарий"),
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Оставьте комментарий'})
    )
    order_cost = forms.IntegerField(
        label=_("Стоимость"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Введите стоимость'})
    )

    class Meta:
        model = TimeTable
        fields = ['name', 'phone', 'email', 'house', 'startdate', 'enddate', 'guests_amount', 'comment', 'order_cost']