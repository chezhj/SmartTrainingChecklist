# Generated by Django 4.1 on 2022-08-30 21:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklist', '0008_attribute_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='attribute',
            name='order',
            field=models.PositiveIntegerField(default=1),
            preserve_default=False,
        ),
    ]
