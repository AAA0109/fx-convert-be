import logging

from django.db import migrations
from django.db.models import Count

logger = logging.getLogger(__name__)


def clean_duplicated_details(apps, *__):
    """
    Method to remove duplicated fx balance details
    """
    FXBalanceDetail = apps.get_model('corpay', 'FXBalanceDetail')
    qs = FXBalanceDetail.objects.values('fx_balance_id', 'order_number', 'transaction_id') \
        .annotate(cnt=Count('transaction_id')).filter(cnt__gt=1)

    for data in qs:
        qs_filter = FXBalanceDetail.objects.values('id') \
                        .filter(fx_balance_id=data['fx_balance_id'],
                                order_number=data['order_number'],
                                transaction_id=data['transaction_id']) \
                        .order_by('pk')[1:]
        FXBalanceDetail.objects.filter(pk__in=qs_filter).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('corpay', '0022_fxbalance_status'),
    ]

    operations = [
        migrations.RunPython(clean_duplicated_details),
        migrations.AlterModelOptions(
            name='fxbalancedetail',
            options={},
        ),
        migrations.AlterUniqueTogether(
            name='fxbalancedetail',
            unique_together={('fx_balance', 'order_number', 'transaction_id')},
        ),
    ]
