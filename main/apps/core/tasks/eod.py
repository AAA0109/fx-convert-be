from itertools import combinations_with_replacement
import json
from celery import shared_task, chain, group, chord, signature
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone
import time
from hdlib.DateTime.Date import Date
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
import gc

logger = get_task_logger(__name__)


@shared_task
def process_download_batch(batch):
    from main.apps.dataprovider.tasks.download_market_data import download_market_data_by_profile

    for profile_id in batch:
        download_market_data_by_profile.apply_async(args=[profile_id])

    # Force garbage collection after each batch
    gc.collect()

    return f"Processed batch of {len(batch)} profiles"


@shared_task
def process_all_download_batches(profile_ids):
    # Chunk the profile_ids into smaller batches
    DOWNLOAD_BATCH_SIZE = 10  # Adjust this value as needed
    download_input_batches = [profile_ids[i:i + DOWNLOAD_BATCH_SIZE]
                              for i in range(0, len(profile_ids), DOWNLOAD_BATCH_SIZE)]
    return chain(*[process_download_batch.si(batch) for batch in download_input_batches])()


@shared_task
def process_import_batch(batch):
    from main.apps.dataprovider.tasks.import_market_data import import_market_data

    for profile_id in batch:
        import_market_data.apply_async(args=[profile_id])

    # Force garbage collection after each batch
    gc.collect()


@shared_task
def process_all_import_batches(profile_ids):
    # Chunk the profile_ids into smaller batches
    IMPORT_BATCH_SIZE = 10  # Adjust this value as needed
    import_input_batches = [profile_ids[i:i + IMPORT_BATCH_SIZE]
                            for i in range(0, len(profile_ids), IMPORT_BATCH_SIZE)]
    return chain(*[process_import_batch.si(batch) for batch in import_input_batches])()


@shared_task
def process_covariance_estimator_batch(batch):
    from main.apps.marketdata.tasks.create_covariance_estimator import create_covariance_estimator

    # Process in smaller chunks to manage memory
    chunk_size = 1000
    for i in range(0, len(batch), chunk_size):
        chunk = batch[i:i+chunk_size]
        for item in chunk:
            create_covariance_estimator.apply_async(args=item)

        # Force garbage collection after each chunk
        gc.collect()

    return f"Processed batch of {len(batch)} items"


@shared_task
def process_all_covariance_estimator_batches(estimator_input):
    # Chunk the estimator_input into smaller batches
    COVAR_BATCH_SIZE = 5000
    estimator_input_batches = [estimator_input[i:i + COVAR_BATCH_SIZE]
                               for i in range(0, len(estimator_input), COVAR_BATCH_SIZE)]
    return chain(*[process_covariance_estimator_batch.si(batch) for batch in estimator_input_batches])()


@shared_task
def process_fxspotvol_batch(batch):
    from main.apps.marketdata.tasks.create_fxspot_vol_estimators import create_fxspot_vol_estimator

    # Process in smaller chunks to manage memory
    chunk_size = 100
    for i in range(0, len(batch), chunk_size):
        chunk = batch[i:i+chunk_size]
        for pair_id in chunk:
            create_fxspot_vol_estimator.apply_async(
                args=[pair_id], ignore_result=True)

        # Force garbage collection after each chunk
        gc.collect()

    return f"Processed batch of {len(batch)} items"


@shared_task
def process_all_fxspotvol_batches(fx_pairs):
    # Chunk the fx_pairs into smaller batches
    FXSPOTVOL_BATCH_SIZE = 500
    fxspotvol_input_batches = [fx_pairs[i:i + FXSPOTVOL_BATCH_SIZE]
                               for i in range(0, len(fx_pairs), FXSPOTVOL_BATCH_SIZE)]
    return chain(*[process_fxspotvol_batch.si(batch) for batch in fxspotvol_input_batches])()


def get_profiles_data_downloader():
    from main.apps.dataprovider.models import Profile, Source
    return list(Profile.objects.filter(
        source__data_type__in=[
            Source.DataType.GCP,
            Source.DataType.LOCAL_STORAGE,
            Source.DataType.SFTP
        ]).values_list('id', flat=True))


def get_fx_profiles():
    from main.apps.dataprovider.models import Profile
    fx_spot_ct_id = ContentType.objects.get(
        app_label='marketdata', model='fxspot').id
    fx_forward_ct_id = ContentType.objects.get(
        app_label='marketdata', model='fxforward').id

    profiles__fx_spot = list(Profile.objects.filter(target_id=fx_spot_ct_id,
                                                    source__data_type='sftp',
                                                    source__data_provider__provider_handler='ice').values_list('id', flat=True))
    profiles__fx_forward = list(Profile.objects.filter(target_id=fx_forward_ct_id,
                                                       source__data_type='sftp',
                                                       source__data_provider__provider_handler='ice').values_list('id', flat=True))
    return profiles__fx_spot, profiles__fx_forward


def get_profile_ids_from_existing_tasks():
    from django_celery_beat.models import PeriodicTask
    profile_ids = []
    periodic_tasks = PeriodicTask.objects.filter(
        enabled=True,
        task__in=[
            'main.apps.dataprovider.tasks.import_market_data.import_market_data',
            'main.apps.dataprovider.tasks.corpay_triangulate_marketdata.workflow_corpay_spot_forward_import_triangulate_marketdata'
        ]
    )
    for periodic_task in periodic_tasks:
        try:
            if periodic_task.task == 'main.apps.dataprovider.tasks.corpay_triangulate_marketdata.workflow_corpay_spot_forward_import_triangulate_marketdata':
                task_kwargs = json.loads(periodic_task.kwargs)
                profile_ids.extend(task_kwargs.values())
            elif periodic_task.task == 'main.apps.dataprovider.tasks.import_market_data.import_market_data':
                task_args = json.loads(periodic_task.args)
                profile_ids.extend(
                    [arg for arg in task_args if isinstance(arg, int)])
        except Exception as e:
            logger.error(
                f"[eod_master_workflow] Error processing periodic task: {str(e)}", exc_info=True)
    return profile_ids


def get_other_profiles(profiles__fx_spot, profiles__fx_forward, profile_ids_from_existing_importer_task):
    from main.apps.dataprovider.models import Profile
    exclude_ids = profiles__fx_spot + profiles__fx_forward + \
        profile_ids_from_existing_importer_task
    return list(Profile.objects.exclude(id__in=exclude_ids).values_list('id', flat=True))


def get_fx_pairs():
    from main.apps.marketdata.models import FxSpot
    return list(FxSpot.objects.values_list('pair__id', flat=True).distinct())


def get_companies_to_hedge():
    from main.apps.account.models import Company
    return list(Company.objects.filter(
        Q(broker_accounts__broker__name="IBKR") | Q(
            corpaysettings__isnull=False)
    ).values_list('id', flat=True))


@shared_task
def log_progress(message):
    logger.info(f"[eod_master_workflow] Progress: {message}")
    return message


@shared_task(
    bind=True,
    time_limit=4 * 60 * 60,
    max_retries=5,
    name='eod_master_workflow',
    tags=['eod']
)
def eod_master_workflow(self):
    start_time = time.time()

    try:
        logger.info(
            f"[eod_master_workflow] starting on {timezone.now().date()} at {start_time}")

        # Import necessary models and tasks
        from main.apps.currency.models import Currency
        from main.apps.dataprovider.tasks.import_market_data import import_market_data
        from main.apps.marketdata.tasks.cache_fxspot_rate_time_series import cache_fx_spot_rates
        from main.apps.hedge.tasks.cache_a_currency_universe import cache_currency_universe
        from main.apps.margin.tasks.margin_health import check_margin_health
        from main.apps.billing.tasks.collect_daily_fees import collect_daily_fees
        from main.apps.billing.tasks.aum_fee_flow_for_company import aum_fee_flow_for_company
        from main.apps.dataprovider.tasks.download_market_data import download_market_data_by_profile

        # Fetch necessary data
        profiles_data_downloader = get_profiles_data_downloader()
        profiles__fx_spot, profiles__fx_forward = get_fx_profiles()
        profile_ids_from_existing_importer_task = get_profile_ids_from_existing_tasks()
        profiles__other = get_other_profiles(
            profiles__fx_spot, profiles__fx_forward, profile_ids_from_existing_importer_task)
        fx_pairs = get_fx_pairs()
        currencies = list(Currency.objects.filter(
            mnemonic__in=['USD']).values_list('id', flat=True))
        companies_to_hedge = get_companies_to_hedge()
        companies_to_collect_daily_fee = companies_to_hedge
        companies_to_run_aum_fee_flow = companies_to_hedge

        min_date = Date(day=1, month=1, year=2010)

        estimator_input = [
            [pair1, pair2, 0.99, min_date.date().__str__()]
            for pair1, pair2 in combinations_with_replacement(fx_pairs, 2)
        ]

        # Create task groups
        data_download_group = group([
            process_all_download_batches.si(profiles_data_downloader),
            log_progress.si("Data download completed")
        ])

        data_import_group = group([
            process_all_import_batches.si(profiles__fx_spot),
            process_all_import_batches.si(profiles__fx_forward),
            process_all_import_batches.si(profiles__other),
            log_progress.si("Data import completed")
        ])

        cache_fx_spot_rates_group = group([
            cache_fx_spot_rates.si(pair_id, min_date) for pair_id in fx_pairs
        ] + [log_progress.si("FX spot rates caching completed")])

        covariance_estimator_group = group([
            process_all_covariance_estimator_batches.si(estimator_input),
            log_progress.si("Covariance estimation completed")
        ])

        fxspot_vol_estimator_group = group([
            process_all_fxspotvol_batches.si(fx_pairs),
            log_progress.si("FX spot volatility estimation completed")
        ])

        currency_universe_group = group([
            cache_currency_universe.si(currency_id=id, ref_date=Date.today().date().__str__()) for id in currencies
        ] + [log_progress.si("Currency universe caching completed")])

        company_tasks_group = group([
            check_margin_health.si(company_id=id) for id in companies_to_hedge
        ] + [
            collect_daily_fees.si(company_id=id) for id in companies_to_collect_daily_fee
        ] + [
            aum_fee_flow_for_company.si(company_id=id) for id in companies_to_run_aum_fee_flow
        ] + [log_progress.si("Company tasks completed")])

        # Execute all groups in sequence using a chord
        workflow = chord([
            data_download_group,
            data_import_group,
            cache_fx_spot_rates_group,
            covariance_estimator_group,
            fxspot_vol_estimator_group,
            currency_universe_group,
            company_tasks_group
        ], log_progress.si("EOD master workflow completed"))

        result = workflow.apply_async()
        logger.info(
            f"[eod_master_workflow] Workflow started with id: {result.id}")

    except Exception as ex:
        logger.exception(f"[eod_master_workflow] Error: {str(ex)}")
        retry_in = 2 ** self.request.retries  # Exponential backoff
        raise self.retry(exc=ex, countdown=retry_in)
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(
            f"[eod_master_workflow] Execution time: {execution_time / 60:.2f} minutes")
        # Force garbage collection at the end of the workflow
        gc.collect()
        return f"[eod_master_workflow] Execution time: {execution_time / 60:.2f} minutes"
