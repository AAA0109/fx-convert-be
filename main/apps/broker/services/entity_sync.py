from typing import Union
from datetime import datetime

from main.apps.settlement.models.beneficiary import Beneficiary
from main.apps.settlement.models.wallet import Wallet
from main.apps.broker.models import Broker
from main.apps.broker.models.entity_sync import EntitySyncEntity


class EntitySyncService:
    @staticmethod
    def sync_entity(entity: Union[Beneficiary, Wallet], broker: Broker):
        entity_type = EntitySyncEntity.SyncEntityType.BENEFICIARY if isinstance(entity, Beneficiary) else EntitySyncEntity.SyncEntityType.WALLET
        entity_id = str(entity.beneficiary_id) if isinstance(entity, Beneficiary) else str(entity.wallet_id)

        sync_state, created = EntitySyncEntity.objects.get_or_create(
            entity_type=entity_type,
            entity_id=entity_id,
            broker=broker
        )

        if sync_state.status == EntitySyncEntity.SyncStatus.PENDING:
            try:
                # Perform the synchronization logic here
                # This may involve making API calls to the broker to sync the entity data

                # Example synchronization logic for beneficiaries
                if isinstance(entity, Beneficiary):
                    # Sync beneficiary data to the broker
                    ...

                # Example synchronization logic for wallets
                elif isinstance(entity, Wallet):
                    # Sync wallet data to the broker
                    ...

                sync_state.status = EntitySyncEntity.SyncStatus.SUCCESS
                sync_state.last_synced_at = datetime.utcnow()
                sync_state.save()

            except Exception as e:
                sync_state.status = EntitySyncEntity.SyncStatus.FAILED
                sync_state.save()
                raise e

    @staticmethod
    def sync_entities(broker: Broker):
        # Sync beneficiaries
        beneficiaries = Beneficiary.objects.filter(broker=broker)
        for beneficiary in beneficiaries:
            EntitySyncService.sync_entity(beneficiary, broker)

        # Sync wallets
        wallets = Wallet.objects.filter(broker=broker)
        for wallet in wallets:
            EntitySyncService.sync_entity(wallet, broker)
