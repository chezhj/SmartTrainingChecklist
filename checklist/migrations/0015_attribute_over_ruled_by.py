# Generated by Django 4.1 on 2023-09-20 21:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('checklist', '0014_attribute_show'),
    ]

    operations = [
        migrations.AddField(
            model_name='attribute',
            name='over_ruled_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='checklist.attribute'),
        ),
    ]
