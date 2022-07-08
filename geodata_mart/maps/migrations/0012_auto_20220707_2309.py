# Generated by Django 3.2.13 on 2022-07-07 23:09

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0011_alter_job_job_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='tasks',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=36), blank=True, null=True, size=None),
        ),
        migrations.AlterField(
            model_name='job',
            name='job_id',
            field=models.CharField(blank=True, default='21fea5a375dc402684cb4a5fcce5f5ef', max_length=32, null=True, unique=True, verbose_name='Job ID'),
        ),
        migrations.AlterField(
            model_name='job',
            name='layers',
            field=models.ManyToManyField(blank=True, to='maps.Layer', verbose_name='Map Layers'),
        ),
    ]