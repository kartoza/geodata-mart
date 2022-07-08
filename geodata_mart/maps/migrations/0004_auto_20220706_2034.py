# Generated by Django 3.2.13 on 2022-07-06 20:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0003_auto_20220706_0201'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='job_id',
            field=models.CharField(default='9fef7da35d1c4b24b1f52b22cb93d52f', max_length=32, unique=True, verbose_name='Job ID'),
        ),
        migrations.AlterUniqueTogether(
            name='layer',
            unique_together={('short_name', 'project_id')},
        ),
    ]