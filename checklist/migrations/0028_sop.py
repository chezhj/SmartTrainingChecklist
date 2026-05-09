"""
Migration 0028: Create the SOP table and add a nullable FK on Procedure.

The FK is nullable here so the data migration (0029) can populate
all existing rows before we make it non-nullable in 0030.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("checklist", "0027_procedure_show_rule_and_idle_datarefs"),
    ]

    operations = [
        migrations.CreateModel(
            name="SOP",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Full aircraft name, e.g. 'Boeing 737-800'",
                        max_length=100,
                    ),
                ),
                (
                    "icao_code",
                    models.CharField(
                        help_text="ICAO type code, e.g. 'B738'",
                        max_length=10,
                    ),
                ),
                (
                    "content_version",
                    models.CharField(
                        help_text="Semver of the checklist content, e.g. '1.0.0'",
                        max_length=20,
                    ),
                ),
                (
                    "release_notes",
                    models.TextField(
                        blank=True,
                        help_text="Human-readable summary of what changed in this content version.",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name="procedure",
            name="sop",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="procedures",
                to="checklist.sop",
            ),
        ),
    ]
