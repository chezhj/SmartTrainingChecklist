# Generated by Django 4.1 on 2024-07-17 18:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklist', '0017_checkitem_action_label_checkitem_dataref_expression_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='procedure',
            name='auto_continue',
            field=models.BooleanField(default=False),
        ),
    ]
