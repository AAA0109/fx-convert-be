from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Iterable, Optional

from django.utils import timezone

from main.apps.account.models import Company
from main.apps.broker.models import BrokerCompany, BrokerProviderOption, Broker
from main.apps.corpay.services.api.dataclasses.settlement_accounts import ViewFXBalanceAccountsParams
from main.apps.corpay.services.corpay import CorPayExecutionServiceFactory
from main.apps.currency.models import Currency
from main.apps.monex.services.monex import MonexApi
from main.apps.nium.services.nium import NiumService
from main.apps.settlement.models.wallet import Wallet, WalletBalance


class WalletService(ABC):

    def __init__(self, company: Company):
        self.company = company

    @abstractmethod
    def sync_wallets_from_broker(self) -> Iterable[Wallet]:
        ...

    @abstractmethod
    def create_or_update_wallet(self, data: Dict, wallet_type: Optional[str] = None) -> Wallet:
        ...

    @abstractmethod
    def update_wallet_balance(self, wallet: Wallet, data: Dict):
        ...


class CorpayWalletService(WalletService):
    def __init__(self, company: Company):
        super().__init__(company)
        factory = CorPayExecutionServiceFactory()
        self.api = factory.for_company(self.company)
        self.broker = Broker.objects.get(
            broker_provider=BrokerProviderOption.CORPAY)

    def sync_wallets_from_broker(self) -> Iterable[Wallet]:
        wallets = []
        settlement_accounts = self.api.list_settlement_accounts()
        data = ViewFXBalanceAccountsParams(includeBalance=True)
        fx_balance_accounts = self.api.list_fx_balance_accounts(data)
        for item in settlement_accounts['items']:
            if item['text'] == 'Bank Accounts':
                for account in item['children']:
                    wallet = self.create_or_update_wallet(
                        account, 'settlement_account')
                    wallets.append(wallet)
        for fx_balance_account in fx_balance_accounts['items']:
            wallet = self.create_or_update_wallet(
                fx_balance_account, 'fxbalance')
            self.update_wallet_balance(wallet, fx_balance_account)
            wallets.append(wallet)

        return wallets

    def create_or_update_wallet(self, data: Dict, wallet_type: Optional[str] = None) -> Wallet:
        if wallet_type == 'settlement_account':
            method = None
            if data['method']['id'] == 'W':
                method = Wallet.WalletMethod.WIRE
            if data['method']['id'] == 'E':
                method = Wallet.WalletMethod.EFT
            wallet, created = Wallet.objects.update_or_create(
                external_id=data['id'],
                company=self.company,
                defaults={
                    'broker': self.broker,
                    'currency': Currency.get_currency(data['currency']),
                    'name': f"{data['text']} - Corpay",
                    'broker_account_id': data['text'],
                    'description': f"Corpay Settlement account for {data['currency']} via {data['method']['text']}",
                    "account_number": data['bankAccount'],
                    'bank_name': data['bankName'],
                    'type': Wallet.WalletType.SETTLEMENT,
                    'status': Wallet.WalletStatus.ACTIVE,
                    'method': method,
                    'last_synced_at': timezone.now(),
                }
            )
        elif wallet_type == 'fxbalance':
            wallet, created = Wallet.objects.update_or_create(
                external_id=data['id'],
                company=self.company,
                defaults={
                    'broker': self.broker,
                    'currency': Currency.get_currency(data['curr']),
                    'name': f"{data['curr']} - {data['account']} - {data['accountName']} - Corpay",
                    'broker_account_id': data['text'],
                    'description': f"Corpay FX balance account for {data['curr']}",
                    'account_number': data['text'],
                    'bank_name': None,  # FX balance accounts don't have a bank name
                    'type': Wallet.WalletType.WALLET,
                    'status': Wallet.WalletStatus.ACTIVE,
                    'last_synced_at': timezone.now(),
                }
            )
        else:
            raise ValueError(f"Invalid wallet_type: {wallet_type}")

        return wallet

    def update_wallet_balance(self, wallet: Wallet, data: Dict):
        if wallet.type != Wallet.WalletType.WALLET:
            # Skip balance update for non-FX balance accounts
            return

        WalletBalance.objects.create(
            wallet=wallet,
            ledger_balance=Decimal(data.get('ledgerBalance', '0')),
            balance_held=Decimal(data.get('balanceHeld', '0')),
            available_balance=Decimal(data.get('availableBalance', '0')),
            timestamp=timezone.now()
        )

        # Optionally, update a 'last_synced_at' field on the Wallet model
        wallet.last_synced_at = timezone.now()
        wallet.save(update_fields=['last_synced_at'])


class NiumWalletService(WalletService):
    def __init__(self, company):
        super().__init__(company)
        self.api = NiumService()
        self.api.init_company(company)
        self.broker = Broker.objects.get(
            broker_provider=BrokerProviderOption.NIUM)

    def sync_wallets_from_broker(self) -> Iterable[Wallet]:
        wallets = []
        customers = self.api.list_customers()
        for customer in customers['content']:
            if customer['customerHashId'] != self.company.niumsettings.customer_hash_id:
                continue
            for account_detail in customer['accountDetails']:
                wallet_hash_id = account_detail['walletHashId']
                wallet_balances = self.api.get_wallet_balance(wallet_hash_id)

                for balance_data in wallet_balances:
                    # Embed wallet_hash_id in the data dictionary
                    balance_data['wallet_hash_id'] = wallet_hash_id
                    wallet = self.create_or_update_wallet(balance_data)
                    self.update_wallet_balance(wallet, balance_data)
                    wallets.append(wallet)

        return wallets

    def create_or_update_wallet(self, data: Dict, wallet_type: Optional[str] = None) -> Wallet:
        currency_code = data['curSymbol']
        wallet_hash_id = f"{data['wallet_hash_id']}_{currency_code}"
        default_name = f"{currency_code} - {wallet_hash_id} - Nium Wallet"

        wallet, created = Wallet.objects.update_or_create(
            external_id=wallet_hash_id,
            company=self.company,
            defaults={
                'broker': self.broker,
                'currency': Currency.get_currency(currency_code),
                'name': default_name,
                'broker_account_id': wallet_hash_id,
                'description': f"Nium wallet for {currency_code}",
                # Using isoCode as account_number
                'account_number': data['isoCode'],
                'type': Wallet.WalletType.WALLET,
                'status': Wallet.WalletStatus.ACTIVE,
                'last_synced_at': timezone.now(),
            }
        )

        return wallet

    def update_wallet_balance(self, wallet: Wallet, data: Dict):
        WalletBalance.objects.create(
            wallet=wallet,
            ledger_balance=Decimal(data['balance']),
            balance_held=Decimal(data['withHoldingBalance']),
            available_balance=Decimal(
                data['balance']) - Decimal(data['withHoldingBalance']),
            timestamp=timezone.now()
        )

        # Update the last_synced_at field on the Wallet model
        wallet.last_synced_at = timezone.now()
        wallet.save(update_fields=['last_synced_at'])


class MonexWalletService(WalletService):
    def __init__(self, company: Company):
        super().__init__(company)
        self.api = MonexApi()
        self.broker = Broker.objects.get(
            broker_provider=BrokerProviderOption.MONEX)

    def sync_wallets_from_broker(self) -> Iterable[Wallet]:
        wallets = []
        funding_sources = self.api.get_funding_sources(company=self.company)
        for funding_source in funding_sources:
            wallet = self.create_or_update_wallet(
                funding_source, wallet_type='funding_source')
            wallets.append(wallet)
        holding_accounts = self.api.get_holding_accounts(company=self.company)
        holding_accounts = self._filter_holding_accounts(holding_accounts)
        holding_accounts = self._add_balance_info(holding_accounts)
        for holding_account in holding_accounts:
            wallet = self.create_or_update_wallet(
                holding_account, wallet_type='holding_account')
            self.update_wallet_balance(wallet, holding_account)
            wallets.append(wallet)

        return wallets

    def create_or_update_wallet(self, data: Dict, wallet_type: Optional[str] = None) -> Wallet:
        if wallet_type == 'funding_source':
            account_type = self.api.monex_id_to_account_type(
                data['accountTypeId'])
            if account_type == 'Checking Debit':
                account_type = Wallet.WalletAccountType.CHECKING
            if account_type == 'Saving Debit':
                account_type = Wallet.WalletAccountType.SAVING
            currency = self.api.monex_id_to_currency(data['currencyId'])
            status = Wallet.WalletStatus.ACTIVE if data['isEnabled'] else Wallet.WalletStatus.INACTIVE
            wallet, created = Wallet.objects.update_or_create(
                external_id=data['id'],
                company=self.company,
                defaults={
                    "broker": self.broker,
                    "currency": currency,
                    "name": f"{currency} - {data['bank']['name']} - Funding Source - Monex",
                    "broker_account_id": data['id'],
                    "description": f"Monex funding source for {currency} via {account_type}",
                    "account_number": data['accountNumber'],
                    "bank_name": data['bank']['name'],
                    "type": Wallet.WalletType.SETTLEMENT,
                    "status": status,
                    "account_type": account_type,
                    "last_synced_at": timezone.now()
                }
            )
        elif wallet_type == 'holding_account':
            currency = Currency.get_currency(data['currencyCode'])
            wallet, created = Wallet.objects.update_or_create(
                external_id=data['currencyCode'],
                company=self.company,
                defaults={
                    "broker": self.broker,
                    "currency": currency,
                    "name": f"{data['currencyCode']} - {self.company.name} - Holding Account - Monex",
                    "broker_account_id": data['currencyId'],
                    "description": f"Monex Holding account for {data['currencyCode']}",
                    "type": Wallet.WalletType.WALLET,
                    "status": Wallet.WalletStatus.ACTIVE,
                    "last_synced_at": timezone.now()
                }
            )
        else:
            raise ValueError(f"Invalid wallet_type: {wallet_type}")

        return wallet

    def update_wallet_balance(self, wallet: Wallet, data: Dict):
        WalletBalance.objects.create(
            wallet=wallet,
            ledger_balance=Decimal(data.get('balance', 0)),
            balance_held=Decimal(0),
            available_balance=Decimal(data.get('balance', 0)),
            timestamp=timezone.now()
        )
        wallet.last_synced_at = timezone.now()
        wallet.save(update_fields=['last_synced_at'])

    def _filter_holding_accounts(self, holding_accounts: Iterable[Dict]):
        return [holding_account for holding_account in holding_accounts if holding_account['entityId'] == int(self.company.monexcompanysettings.entity_id)]

    def _add_balance_info(self, holding_accounts: Iterable[Dict]):
        reports = self.api.get_holding_reports(self.company)
        balance_map = {int(report['ccyId']): report['amount']
                       for report in reports['accounts']}

        for holding_account in holding_accounts:
            holding_account['balance'] = balance_map.get(
                int(holding_account['currencyId']), 0)

        return holding_accounts


class WalletServiceFactory(ABC):
    def __init__(self, company: Company):
        self.company = company

    def create_wallet_services(self, broker: Optional[str] = None) -> Iterable[WalletService]:
        wallet_services = []
        broker_companies = BrokerCompany.objects.filter(company=self.company)

        if broker:
            broker_companies = broker_companies.filter(
                broker=broker, active=True)

        for broker_company in broker_companies:
            if broker_company.broker == BrokerProviderOption.CORPAY:
                if not hasattr(self.company, 'corpaysettings') or \
                    not self.company.corpaysettings:
                        continue
                corpay_service = CorpayWalletService(self.company)
                wallet_services.append(corpay_service)
            elif broker_company.broker == BrokerProviderOption.NIUM:
                if not hasattr(self.company, 'niumsettings') or \
                    not self.company.niumsettings:
                    continue
                nium_service = NiumWalletService(self.company)
                wallet_services.append(nium_service)
            elif broker_company.broker == BrokerProviderOption.MONEX:
                if not hasattr(self.company, 'monexcompanysettings') or \
                    not self.company.monexcompanysettings:
                    continue
                monex_service = MonexWalletService(self.company)
                wallet_services.append(monex_service)

        return wallet_services
