# Generated manually for added RentObject fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_rentobject_extra_pet_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentobject',
            name='address',
            field=models.CharField(blank=True, max_length=255, verbose_name='Адрес'),
        ),
        migrations.AddField(
            model_name='rentobject',
            name='pets_allowed',
            field=models.BooleanField(default=False, verbose_name='Разрешено с питомцами'),
        ),
    ]
