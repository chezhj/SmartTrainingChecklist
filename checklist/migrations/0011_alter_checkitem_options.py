# Generated by Django 4.1 on 2023-07-22 18:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('checklist', '0010_checkitem_step'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='checkitem',
            options={'ordering': ['step']},
        ),
    ]
