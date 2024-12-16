import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql import ResolveInfo

from main.apps.account.models.company import Company
from main.apps.account.models.account import Account
from main.apps.account.models.cashflow import CashFlow
from main.apps.account.models.installment_cashflow import InstallmentCashflow
from main.apps.core.utils.graphql import is_authenticated


class CashFlowNode(DjangoObjectType):
    class Meta:
        model = CashFlow



class InstallmentCashFlowNode(DjangoObjectType):
    class Meta:
        model = InstallmentCashflow


class AccountNode(DjangoObjectType):
    class Meta:
        model = Account
        fields = ("id", "company", "name", "created", "is_active", "type")

    cashflows = graphene.List(CashFlowNode)
    installment_cashflows = graphene.List(InstallmentCashFlowNode)

    def resolve_cashflows(self, info: ResolveInfo):
        return CashFlow.objects.filter(account=self)

    def resolve_installment_cashflow(self, info: ResolveInfo):
        return InstallmentCashflow.objects.filter(account=self)


class CompanyNode(DjangoObjectType):
    class Meta:
        model = Company
        fields = ("id", "name", "created", "currency", "status")

    accounts = graphene.List(AccountNode)

    def resolve_accounts(self, info: ResolveInfo):
        return Account.objects.filter(company=self)


class Query(graphene.ObjectType):
    company = graphene.Field(CompanyNode)
    account = graphene.List(AccountNode)

    def resolve_company(self, info: ResolveInfo):
        return Company.objects.get(user=info.context.user) if is_authenticated(info) else None

    def resolve_account(self, info: ResolveInfo):
        return Account.objects.filter(company=info.context.user.company) if is_authenticated(info) else None


schema = graphene.Schema(query=Query)
