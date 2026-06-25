# Generated manually for the Feedback model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_timetable_addon_banya_timetable_addon_chan'),
    ]

    operations = [
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Имя')),
                ('phone', models.CharField(max_length=30, verbose_name='Телефон')),
                ('message', models.TextField(blank=True, max_length=2000, verbose_name='Сообщение')),
                ('is_processed', models.BooleanField(default=False, verbose_name='Обработано')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Дата отправки')),
            ],
            options={
                'verbose_name': 'Обращение из формы обратной связи',
                'verbose_name_plural': 'Обращения из формы обратной связи',
                'ordering': ('-created',),
            },
        ),
    ]
