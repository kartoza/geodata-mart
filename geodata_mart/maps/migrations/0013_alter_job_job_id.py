# Generated by Django 3.2.13 on 2022-07-08 09:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0012_auto_20220707_2309'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='job_id',
            field=models.CharField(blank=True, default='89657a89f69340d7958f661fcd0337ea', max_length=32, null=True, unique=True, verbose_name='Job ID'),
        ),
    ]