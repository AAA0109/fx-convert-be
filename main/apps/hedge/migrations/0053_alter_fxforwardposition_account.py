# Generated by Django 4.2.3 on 2023-12-09 19:31

from django.db import migrations, models
import django.db.models.deletion


def set_forward_accounts(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.

    FxForwardPosition = apps.get_model("hedge", "FxForwardPosition")
    for fx_forward in FxForwardPosition.objects.all():
        # Protection against the cashflow being null.
        if fx_forward.cashflow:
            fx_forward.account = fx_forward.cashflow.account
            fx_forward.save()


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0086_merge_20231208_1517"),
        ("hedge", "0052_merge_20231208_1516"),
    ]

    operations = [
        # Run the set_forward_accounts function to fill in all the accounts for all the fx forwards.
        migrations.RunPython(set_forward_accounts),

        #
        migrations.AlterField(
            model_name="fxforwardposition",
            name="account",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="account.account", null=True
            ),
        ),
    ]
