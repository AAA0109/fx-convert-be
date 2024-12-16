import logging
from abc import ABC

from django.conf import settings
from django.forms import model_to_dict
from django.utils.text import slugify

from main.apps.account.models import Account, Company
from main.apps.history.models import AccountSnapshot, AccountSnapshotTemplateData

logger = logging.getLogger(__name__)


class AccountSnapshotTemplateService(ABC):
    @staticmethod
    def create_template_from_account(account: Account):
        template_name = account.name
        template_uuid = slugify(f"{account.id}-{template_name}")
        template_source = settings.APP_ENVIRONMENT
        qs = AccountSnapshotTemplateData.objects.filter(
            template_uuid=template_uuid
        )
        if qs.count() > 0:
            logger.debug(f"Deleting snapshot template with id: {template_uuid}")
            qs.delete()
        logger.debug(f"Generating snapshot template with id: {template_uuid}")
        template_data = []
        for snapshot in AccountSnapshot.objects.filter(account=account):
            snapshot_dict = model_to_dict(snapshot, exclude=['account', 'id'])
            snapshot_dict.update({
                'template_id': snapshot.pk,
                'template_uuid': template_uuid,
                'template_name': template_name,
                'template_source': template_source
            })
            template_data_obj = AccountSnapshotTemplateData(**snapshot_dict)
            template_data.append(template_data_obj)

        return AccountSnapshotTemplateData.objects.bulk_create(template_data)

    @staticmethod
    def restore_template_for_company(company: Company):
        for config in company.companysnapshotconfiguration_set.all():
            account_id = config.account_id
            template_uuid = config.template_uuid
            account = Account.objects.get(pk=account_id)
            AccountSnapshotTemplateService.restore_template_for_account(account=account, template_uuid=template_uuid)


    @staticmethod
    def restore_template_for_account(account: Account, template_uuid: str):
        snapshots_data = AccountSnapshotTemplateData.objects.filter(template_uuid=template_uuid)
        AccountSnapshot.objects.filter(account=account).delete()
        snapshots_to_create = []
        for snapshot_data in snapshots_data:
            snapshot_data_dict = model_to_dict(snapshot_data, exclude=[
                'template_name',
                'template_id',
                'template_uuid',
                'template_source',
                'last_snapshot',
            ])
            snapshot_data_dict['account'] = account
            snapshots_to_create.append(AccountSnapshot(**snapshot_data_dict))
        AccountSnapshot.objects.bulk_create(snapshots_to_create)
