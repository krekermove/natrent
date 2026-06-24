from django.db import models


class TimeTable(models.Model):
    name = models.CharField(max_length=50, verbose_name="Имя")
    phone = models.CharField(max_length=18, verbose_name="Номер телефона")
    email = models.EmailField(max_length=254, verbose_name="Электронная почта")
    house = models.ForeignKey('RentObject', on_delete=models.CASCADE, related_name="timetables", verbose_name="Название объекта")
    startdate = models.DateField(verbose_name="Дата заселения")
    enddate = models.DateField(verbose_name="Дата выезда")
    guests_amount = models.PositiveIntegerField(verbose_name="Количество гостей")
    children_under_3 = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество детей до 3 лет",
    )
    has_pet = models.BooleanField(default=False, verbose_name="Наличие питомца")
    addon_banya = models.BooleanField(default=False, verbose_name="Доп. услуга: баня")
    addon_chan = models.BooleanField(default=False, verbose_name="Доп. услуга: сибирский чан")
    comment = models.TextField(max_length=200, null=True, blank=True, default=None, verbose_name="Комментарий")
    order_cost = models.PositiveIntegerField(verbose_name="Стоимость заказа")
    status = models.BooleanField(default=True, blank=True, verbose_name="Статус аренды")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"

    def save(
        self,
        *args,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        houses = TimeTable.objects.filter(house=self.house)
        for house in houses:
            if house.startdate < self.startdate < house.enddate or house.startdate < self.enddate < house.enddate:
                raise ValueError("На эти даты дом уже забронирован.")
            elif self.startdate < house.startdate and self.enddate > house.enddate:
                raise ValueError("На эти даты дом уже забронирован.")
        if self.guests_amount > self.house.max_guests:
            raise ValueError("Количество гостей превышает максимальное.")
        return super().save(force_insert=False, force_update=False, using=None, update_fields=None)


class RentObject(models.Model):
    name = models.CharField(max_length=50, verbose_name="Название объекта")
    address = models.CharField(max_length=255, blank=True, verbose_name="Адрес")
    img1 = models.ImageField(upload_to='houses',
                              blank=True)
    img2 = models.ImageField(upload_to='houses',
                             blank=True)
    img3 = models.ImageField(upload_to='houses',
                             blank=True)
    img4 = models.ImageField(upload_to='houses',
                             blank=True)
    description = models.TextField(max_length=1000, verbose_name="Описание")
    max_guests = models.PositiveIntegerField(verbose_name="Максимальное количеcтво гостей")
    price = models.PositiveIntegerField(verbose_name="Стоимость")
    extra_guest_fee = models.PositiveIntegerField(
        default=0,
        verbose_name="Дополнительная плата за гостя",
        help_text="Добавляется к стоимости брони за каждого дополнительного гостя "
                  "(гость сверх 2, а также ребёнок старше 3 лет)",
    )
    extra_pet_fee = models.PositiveIntegerField(
        default=0,
        verbose_name="Дополнительная плата за питомца",
        help_text="Добавляется к стоимости брони за каждого питомца",
    )
    pets_allowed = models.BooleanField(
        default=False,
        verbose_name="Разрешено с питомцами",
    )

    class Meta:
        verbose_name = "Объект аренды"
        verbose_name_plural = "Объекты аренды"

    def __str__(self):
        return self.name


class DateObjectCost(models.Model):
    date = models.DateField(verbose_name="Дата")
    house = models.ForeignKey(RentObject, on_delete=models.CASCADE, related_name="datecost", verbose_name="Объект")
    cost = models.PositiveIntegerField(verbose_name="Стоимость")

    class Meta:
        verbose_name = "Стоимость объекта на определенную дату"
        verbose_name_plural = "Стоимости объектов на определенную дату"

    def __str__(self):
        return f"{self.date} | {self.house.name} | {self.cost}"
