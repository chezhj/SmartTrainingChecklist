from django.db import migrations, models


def set_initial_category(apps, schema_editor):
    Procedure = apps.get_model("checklist", "Procedure")
    Procedure.objects.exclude(show_rule__isnull=True).update(category="situational")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("checklist", "0032_add_flightsession_show_rule_state"),
    ]

    operations = [
        migrations.AlterField(
            model_name="procedure",
            name="show_rule",
            field=models.JSONField(
                blank=True,
                null=True,
                help_text=(
                    "Rule evaluated against live datarefs. When true, the procedure is "
                    "auto-navigated/suggested. Null = no auto behaviour. Visibility is "
                    "independent — every procedure is always reachable in the picker."
                ),
            ),
        ),
        migrations.AddField(
            model_name="procedure",
            name="category",
            field=models.CharField(
                choices=[
                    ("normal", "Normal"),
                    ("situational", "Situational"),
                    ("emergency", "Emergency"),
                    ("reference", "Reference"),
                ],
                db_index=True,
                default="normal",
                help_text=(
                    "Grouping bucket for the procedure picker. Behaviour (auto-nav / "
                    "suggested highlight) is driven by show_rule, not by this field."
                ),
                max_length=20,
            ),
        ),
        migrations.RunPython(set_initial_category, noop_reverse),
    ]
