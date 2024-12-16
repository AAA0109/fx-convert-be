import django.db.models.deletion
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import migrations, models


def add_permission(apps, schema_editor):
    content_type = ContentType.objects.get(app_label='corpay', model='manualforwardrequest')
    permission = Permission(
        name='Edit view',
        codename='edit_view',
        content_type=content_type,
    )
    permission.save()


class Migration(migrations.Migration):
    dependencies = [
        ('account', '0089_auto_20240122_1554'),
        ('corpay', '0041_merge_20240116_1546'),
    ]

    operations = [
        migrations.AddField(
            model_name='manualforwardrequest',
            name='cashflow',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='account.cashflow'),
        ),
        migrations.RunPython(add_permission)
    ]
