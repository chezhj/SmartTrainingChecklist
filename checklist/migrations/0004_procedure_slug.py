# Generated by Django 4.1 on 2022-08-12 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklist', '0003_attribute_checkitem_attributes'),
    ]

    operations = [
        migrations.AddField(
            model_name='procedure',
            name='slug',
            field=models.SlugField(default='slug'),
            preserve_default=False,
        ),
    ]
