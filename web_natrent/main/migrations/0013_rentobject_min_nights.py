from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_alter_timetable_created'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentobject',
            name='min_nights',
            field=models.PositiveIntegerField(default=1, verbose_name='Минимальное количество ночей'),
        ),
    ]
