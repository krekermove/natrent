from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_alter_timetable_options_dateobjectcost'),
    ]

    operations = [
        migrations.AddField(
            model_name='timetable',
            name='email',
            field=models.EmailField(default='', max_length=254, verbose_name='Электронная почта'),
            preserve_default=False,
        ),
    ]
