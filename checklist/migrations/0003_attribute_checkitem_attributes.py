# Generated by Django 4.1 on 2022-08-10 09:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklist', '0002_procedure_step'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attribute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=30)),
            ],
        ),
        migrations.AddField(
            model_name='checkitem',
            name='attributes',
            field=models.ManyToManyField(blank=True, related_name='checkItems', to='checklist.attribute'),
        ),
    ]