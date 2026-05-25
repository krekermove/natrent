from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_timetable_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='timetable',
            name='children_under_3',
            field=models.PositiveIntegerField(default=0, verbose_name='Количество детей до 3 лет'),
        ),
        migrations.AddField(
            model_name='timetable',
            name='has_pet',
            field=models.BooleanField(default=False, verbose_name='Наличие питомца'),
        ),
        migrations.AddField(
            model_name='rentobject',
            name='extra_guest_fee',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Добавляется к стоимости брони за каждого дополнительного гостя '
                          '(гость сверх 2, а также ребёнок старше 3 лет)',
                verbose_name='Дополнительная плата за гостя',
            ),
        ),
    ]
