# Generated by Django 4.1 on 2022-08-12 10:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklist', '0006_sessionprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessionprofile',
            name='sessionId',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
