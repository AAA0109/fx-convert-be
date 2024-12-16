from typing import Iterable, Union, Optional

from auditlog.registry import auditlog
from django.db import models, transaction

from main.apps.account.models import Company, CompanyTypes
from main.apps.util import get_or_none

InstallmentTypes = Union['InstallmentCashflow', str, int]


class InstallmentCashflow(models.Model):
    class Meta:
        verbose_name_plural = "installment cashflows"

    # The company the installment belongs in.
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    # The name of the installment cashflow. All elements with the same (company, installment_cashflow_name)
    # are part of the same installment.
    installment_name = models.CharField(max_length=255)

    # ============================================================================
    #  Accessors
    # ============================================================================

    @staticmethod
    @get_or_none
    def get_installment(company_id: CompanyTypes, installment_id: InstallmentTypes) -> 'InstallmentCashflow':
        """
        Get the installment with the given id
        :param company_id: The company the installment belongs in
        :param installment_id: The id of the installment
        :return: The installment with the given id
        """
        company = Company.get_company(company_id)
        if not company:
            raise Company.NotFound(company_id)
        if isinstance(installment_id, int):
            installment = InstallmentCashflow.objects.get(company=company, id=installment_id)
        elif isinstance(installment_id, str):
            installment = InstallmentCashflow.objects.get(company=company, installment_name=installment_id)
        elif isinstance(installment_id, InstallmentCashflow):
            installment = installment_id
        else:
            raise ValueError(f"Unknown installment type: {type(installment_id)}")
        return installment

    @staticmethod
    def create_installment(company_id: CompanyTypes,
                           installment_name: str,
                           cashflows: Optional[Iterable['CashFlow']] = None) -> 'InstallmentCashflow':
        """
        Create a new installment for the given company
        :param cashflows: the cashflows to add to the installment
        :param company_id: The company the installment belongs in
        :param installment_name: The name of the installment
        :return: The newly created installment
        """
        company = Company.get_company(company_id)
        if not company:
            raise Company.NotFound(company_id)
        installment = InstallmentCashflow(company=company, installment_name=installment_name)
        if not cashflows:
            cashflows = []
        with transaction.atomic():
            installment.save()
            for cashflow in cashflows:
                cashflow.save()
                installment.cashflow_set.add(cashflow)
        return installment

    @staticmethod
    def get_installment_cashflows(company_id: CompanyTypes,
                                  installment_id: Union['InstallmentCashflow', int, str]) -> Iterable['CashFlow']:
        """ Get all the cashflows in the named installment. """
        installment = InstallmentCashflow.get_installment(company_id=company_id, installment_id=installment_id)
        if not installment:
            raise InstallmentCashflow.NotFound(installment_id)
        cashflows = installment.cashflow_set.all()
        return cashflows

    @staticmethod
    def installment_exists(company_id: CompanyTypes, installment_id: Union[int, str]) -> bool:
        """ Return whether an installment already exists. """
        installment = InstallmentCashflow.get_installment(company_id=company_id, installment_id=installment_id)
        return installment is not None

    @staticmethod
    def delete_installment(company_id: CompanyTypes, installment_id: Union[int, str]):
        """ Delete an installment. """
        installment = InstallmentCashflow.get_installment(company_id=company_id, installment_id=installment_id)
        if not installment:
            raise InstallmentCashflow.NotFound(installment_id)
        installment.delete()

    class NotFound(Exception):
        def __init__(self, installment_id: Union[int, str, 'InstallmentCashflow']):
            if isinstance(installment_id, int):
                super(InstallmentCashflow.NotFound, self) \
                    .__init__(f"InstallmentCashflow with id:{installment_id} is not found")
            elif isinstance(installment_id, str):
                super(InstallmentCashflow.NotFound, self) \
                    .__init__(f"InstallmentCashflow with name:{installment_id} is not found")
            elif isinstance(installment_id, InstallmentCashflow):
                super(InstallmentCashflow.NotFound, self) \
                    .__init__(f"InstallmentCashflow:{installment_id} is not found")
            else:
                super(InstallmentCashflow.NotFound, self).__init__()


auditlog.register(InstallmentCashflow)
