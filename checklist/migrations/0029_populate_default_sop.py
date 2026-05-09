"""
Migration 0029: Data migration — create the default B738 SOP and assign
all existing Procedure rows to it.
"""

from django.db import migrations


def create_default_sop(apps, schema_editor):
    SOP = apps.get_model("checklist", "SOP")
    Procedure = apps.get_model("checklist", "Procedure")

    sop = SOP.objects.create(
        name="Boeing 737-800",
        icao_code="B738",
        content_version="1.0.0",
        release_notes="Initial SOP version.",
    )
    Procedure.objects.filter(sop=None).update(sop=sop)


def remove_default_sop(apps, schema_editor):
    SOP = apps.get_model("checklist", "SOP")
    Procedure = apps.get_model("checklist", "Procedure")

    Procedure.objects.update(sop=None)
    SOP.objects.filter(icao_code="B738", content_version="1.0.0").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("checklist", "0028_sop"),
    ]

    operations = [
        migrations.RunPython(create_default_sop, remove_default_sop),
    ]
