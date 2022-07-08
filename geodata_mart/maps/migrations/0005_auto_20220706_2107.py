# Generated by Django 3.2.13 on 2022-07-06 21:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0004_auto_20220706_2034'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='job_id',
            field=models.CharField(default='764dfd5c584d49c48b09ead528f2c8e1', max_length=32, unique=True, verbose_name='Job ID'),
        ),
        migrations.AlterField(
            model_name='resultfile',
            name='job_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='maps.job', verbose_name='Job'),
        ),
    ]