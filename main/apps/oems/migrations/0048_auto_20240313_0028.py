from django.db import migrations, transaction
import logging

logger = logging.getLogger(__name__)


def bulk_update_or_create_cny_executions(apps, schema_editor):
    CnyExecution = apps.get_model("oems", "CnyExecution")
    CurrencyDefinition = apps.get_model("corpay", "CurrencyDefinition")
    Company = apps.get_model("account", "Company")
    FxPair = apps.get_model("currency", "FxPair")

    all_currency_definitions = CurrencyDefinition.objects.all()
    fx_pairs = {f"{pair.base_currency}_{pair.quote_currency}": pair for pair in FxPair.objects.all()}
    existing_cny_execs_map = {
        f"{exec.company_id}_{exec.fxpair_id}": exec
        for exec in CnyExecution.objects.all().select_related('company', 'fxpair')
    }

    new_cny_execs, update_cny_execs = [], []

    for company in Company.objects.iterator():
        if not hasattr(company, 'corpaysettings'):
            continue

        for base_def in all_currency_definitions:
            for quote_def in all_currency_definitions:
                if base_def == quote_def:
                    continue  # Skip same currency pairs if not applicable

                pair_key = f"{base_def.currency}_{quote_def.currency}"
                pair = fx_pairs.get(pair_key)

                if not pair:
                    continue  # Skip if no pair found

                cny_exec_key = f"{company.id}_{pair.id}"
                cny_exec = existing_cny_execs_map.get(cny_exec_key)

                rfq_type = 'manual' if base_def.ndf or quote_def.ndf else 'api'

                if cny_exec:
                    cny_exec.rfq_type = rfq_type  # Mark for update
                    update_cny_execs.append(cny_exec)
                else:
                    new_cny_execs.append(CnyExecution(company=company, fxpair=pair, rfq_type=rfq_type))

    with transaction.atomic():
        if new_cny_execs:
            CnyExecution.objects.bulk_create(new_cny_execs, batch_size=1000)
        if update_cny_execs:
            CnyExecution.objects.bulk_update(update_cny_execs, ['rfq_type'], batch_size=1000)

    logger.debug(f"Created {len(new_cny_execs)} new CnyExecutions and updated {len(update_cny_execs)} existing ones.")


class Migration(migrations.Migration):
    dependencies = [
        ('oems', '0047_manualrequest_fee_manualrequest_on_behalf_of'),
    ]

    operations = [
        migrations.RunPython(bulk_update_or_create_cny_executions)
    ]
