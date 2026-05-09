"""
Migration 0030: Make Procedure.sop non-nullable now that every row
has been populated by migration 0029.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("checklist", "0029_populate_default_sop"),
    ]

    operations = [
        migrations.AlterField(
            model_name="procedure",
            name="sop",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="procedures",
                to="checklist.sop",
            ),
        ),
    ]
