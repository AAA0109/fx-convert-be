import json
import logging

import django.db.models.deletion
import django_extensions.db.fields
from django.conf import settings
from django.db import migrations
from django.db import models

from main.apps.corpay.models import FXBalance
from main.apps.corpay.models.api_log import ApiResponseLog

logger = logging.getLogger(__name__)


def update_spot_rate(apps, *_, **__):
    SpotRate = apps.get_model('corpay', 'SpotRate')
    FXBalance = apps.get_model('corpay', 'FXBalance')
    Currency = apps.get_model('currency', 'Currency')
    FxPair = apps.get_model('currency', 'FxPair')

    currencies = {}
    pairs = {}

    def get_currencies(simbol):
        result = currencies.get(simbol)
        if not result:
            result = Currency.objects.get(mnemonic=simbol.upper())
            currencies[simbol] = result
        return result

    def get_pair(pair):
        result = pairs.get(pair)
        if not result:
            result = FxPair.objects.get(base_currency__mnemonic=pair[:3], quote_currency__mnemonic=pair[3:])
            pairs[pair] = result
        return result

    ##################################################################
    # Reading primary quote spot (urls that ends with: "quotes/spot")
    ##################################################################
    print('Reading primary quote spot')
    qs = ApiResponseLog.objects.filter(request_log__url__endswith='/quotes/spot') \
        .values('user_id', 'company_id', 'response', 'created', 'pk')
    total = qs.count()

    add_list = []
    executed = 0
    for item in qs:
        if 'An error has occurred' in item['response']:  # Ignoring results with errors
            continue

        try:
            response_content = json.loads(item['response'].replace("'", '"'))['content']
        except Exception: # Ignoring other errors
            continue

        try:
            add_list.append(SpotRate(
                created=item['created'],
                quote_id=response_content['quoteId'],
                user_id=item['user_id'],
                company_id=item['company_id'],
                rate_value=response_content['rate']['value'],
                rate_lockside=response_content['rate']['lockSide'],
                fx_pair=get_pair(response_content['rate']['rateType']),
                rate_operation=response_content['rate']['operation'],
                payment_currency=get_currencies(response_content['payment']['currency']),
                payment_amount=response_content['payment']['amount'],
                settlement_currency=get_currencies(response_content['settlement']['currency']),
                settlement_amount=response_content['settlement']['amount'],
            ))

            if len(add_list) > 4000:
                SpotRate.objects.bulk_create(add_list)
                executed += len(add_list)
                print(f' {executed} of {total} {round(executed/total*100, 1)}%')
                add_list = []
        except FxPair.DoesNotExist:
            continue
        except Exception as e:
            logger.error(e)
    SpotRate.objects.bulk_create(add_list)

    ##################################################################
    # Reading bulk deal to update SpotRate table with order_number
    # (urls that ends with: "/book")
    ##################################################################
    print('Reading bulk deal to update SpotRate')
    qs = ApiResponseLog.objects.filter(request_log__url__endswith='/book').values('response', 'pk')
    print('total:', qs.count())
    for item in qs:
        try:
            response_content = json.loads(item['response'].replace("'", '"'))['content']
        except:  # Ignoring results with errors
            continue

        try:
            # Update SpotRate
            spot_rate = SpotRate.objects.get(quote_id=response_content['token'])
            spot_rate.order_number = response_content['orderNumber']
            spot_rate.save()

            # Link FXBalance
            for instance in FXBalance.objects.filter(order_number=response_content['orderNumber']):
                spot_rate.fx_balances.add(instance)

        except SpotRate.DoesNotExist:
            continue
        except Exception as e:
            logger.error(e)


class Migration(migrations.Migration):
    dependencies = [
        ('corpay', '0036_auto_20231106_1730'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpotRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created',
                 django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified',
                 django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('quote_id', models.CharField(max_length=32, unique=True)),
                ('rate_value', models.FloatField()),
                ('rate_lockside',
                 models.CharField(choices=[('Payment', 'PAYMENT'), ('Settlement', 'SETTLEMENT')], max_length=24)),
                ('rate_operation',
                 models.CharField(choices=[('Divide', 'DIVIDE'), ('Multiply', 'MULTIPLY')], max_length=24)),
                ('payment_amount', models.FloatField()),
                ('settlement_amount', models.FloatField()),
                ('payment_currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+',
                                                       to='currency.currency')),
                ('fx_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
                ('settlement_currency',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+',
                                   to='currency.currency')),
                ('company',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='account.company')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           to=settings.AUTH_USER_MODEL)),
                ('fx_balances', models.ManyToManyField(to='corpay.fxbalance')),
                ('order_number', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.RunPython(update_spot_rate),
    ]
