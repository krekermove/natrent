# Generated manually for added TimeTable addon fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_rentobject_address_rentobject_pets_allowed'),
    ]

    operations = [
        migrations.AddField(
            model_name='timetable',
            name='addon_banya',
            field=models.BooleanField(default=False, verbose_name='Доп. услуга: баня'),
        ),
        migrations.AddField(
            model_name='timetable',
            name='addon_chan',
            field=models.BooleanField(default=False, verbose_name='Доп. услуга: сибирский чан'),
        ),
    ]
