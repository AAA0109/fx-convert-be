import logging
from datetime import date
from typing import Union, List, Optional, Iterable, Set

import dateutil.rrule
from auditlog.registry import auditlog
from django.conf import settings
from django.db import models
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as __
from django_extensions.db.fields import CreationDateTimeField
from django_extensions.db.models import TimeStampedModel
from hdlib.DateTime.Calendar.Calendar import NullCalendar, CustomCalendar, RollConvention as RollConventionHDL
from hdlib.DateTime.Date import Date
from hdlib.Instrument.CashFlow import CashFlow as CashFlowHDL

from main.apps.account.models import Company
from main.apps.account.models.account import Account, AccountTypes
from main.apps.account.models.installment_cashflow import InstallmentCashflow
from main.apps.currency.models.currency import Currency, CurrencyId, CurrencyTypes
from main.apps.util import get_or_none

logger = logging.getLogger(__name__)


def iter_active_cashflows(cfs: Iterable[Union['CashFlow', CashFlowHDL]],
                          ref_date: Date,
                          max_days_away: int = 730,
                          max_date_in_future: Optional[Date] = None,
                          include_cashflows_on_vd: bool = False,
                          include_end: bool = False,
                          skip_less_than_ref_date: bool = False
                          ) -> Iterable[CashFlowHDL]:
    for cf in cfs:
        if skip_less_than_ref_date and cf.created > ref_date:
            continue
        # So this works with CashFlowHDL in addition to our django model CashFlow objects. This is occasionally useful.
        if isinstance(cf, CashFlowHDL):
            yield cf
        else:
            for hdl_cf in cf.get_hdl_cashflows():
                if hdl_cf.pay_date < ref_date if include_cashflows_on_vd else hdl_cf.pay_date <= ref_date:
                    continue
                days_away = (hdl_cf.pay_date - ref_date).days
                if max_days_away is not None and (
                    days_away > max_days_away if include_end else days_away >= max_days_away):
                    break
                if max_date_in_future is not None and (
                    hdl_cf.pay_date > max_date_in_future if include_end else hdl_cf.pay_date >= max_date_in_future):
                    break
                yield hdl_cf


def get_hdl_cashflows(name: str,
                      amount: float,
                      currency: Currency,
                      calendar,
                      roll_convention,
                      date: Date,
                      is_recurring: bool,
                      periodicity,
                      end_date: Optional[Date] = None
                      ) -> Iterable[CashFlowHDL]:
    """
    Returns the cashflow, defined by its fields, as a list of CashFlowHDL objects.
    """
    calendar = CashFlow.CalendarType.to_hdl_calendar(calendar)
    roll_convention = CashFlow.RollConvention.to_hdl_roll_convention(roll_convention)

    # NOTE: See the "to do" below about end_date
    if end_date:
        end_date = Date.create(year=end_date.year, month=end_date.month, day=end_date.day,
                               hour=23, minute=59, second=59, microsecond=999999)
    else:
        end_date = None

    # TODO: consider what time of date to assign to the cashflows (they are stored as dates not datetimes)
    if is_recurring:
        for d in dateutil.rrule.rrulestr(periodicity, dtstart=date):
            pay_date = calendar.adjust(date=Date.from_datetime_date(d), roll_convention=roll_convention)
            # TODO: self.end_date is a datetime.date, pay_date is a Date (datetime.datetime). These are not
            #  comparable, so I'm converting end_date to a Date (above) and setting the time to a minute before
            #  midnight
            if end_date and end_date < pay_date:
                break
            yield CashFlowHDL(amount=amount, pay_date=pay_date, currency=currency, name=name)
    else:
        pay_date = calendar.adjust(Date.from_datetime_date(date), roll_convention)
        yield CashFlowHDL(amount=amount, pay_date=pay_date, currency=currency, name=name)


class BaseCashFlow(TimeStampedModel):
    created = models.DateTimeField(__('created'), default=timezone.now, null=False, blank=False)

    class Meta:
        abstract = True

    class CalendarType(models.TextChoices):
        NULL_CALENDAR = "NULL_CALENDAR", __("NULL_CALENDAR")  # Every day is a business day
        WESTERN_CALENDAR = "WESTERN_CALENDAR", __("WESTERN_CALENDAR")  # Weekends are the only holidays

        @staticmethod
        def from_name(cal_name: str):
            cal_name = cal_name.upper()
            if cal_name == "NULL" or cal_name == "NULL_CALENDAR":
                return CashFlow.CalendarType.NULL_CALENDAR
            if cal_name == "WESTERN" or cal_name == "WESTERN_CALENDAR":
                return CashFlow.CalendarType.WESTERN_CALENDAR
            raise NotImplementedError(f"Unsupported calendar conversion: {cal_name}")

        @staticmethod
        def to_hdl_calendar(cal: 'CashFlow.CalendarType'):
            if cal == CashFlow.CalendarType.NULL_CALENDAR:
                return NullCalendar()
            if cal == CashFlow.CalendarType.WESTERN_CALENDAR:
                return CustomCalendar.new_western_no_holidays()
            raise NotImplementedError(f"Unsupported calendar conversion: {cal}")

    class RollConvention(models.TextChoices):
        UNADJUSTED = 'UNADJUSTED'  # Don't roll the date
        FOLLOWING = 'FOLLOWING'  # The following business date
        MODIFIED_FOLLOWING = 'MODIFIED_FOLLOWING'
        HALF_MONTH_MODIFIED_FOLLOWING = 'HALF_MONTH_MODIFIED_FOLLOWING'
        PRECEDING = 'PRECEDING'  # The previous business date
        MODIFIED_PRECEDING = 'MODIFIED_PRECEDING'
        NEAREST = 'NEAREST'  # The nearest business date (either up or down)

        @staticmethod
        def from_name(choice_name: Optional[str]):
            if not choice_name:
                return CashFlow.RollConvention.UNADJUSTED

            choice_name = choice_name.upper()
            if choice_name == "UNADJUSTED" or len(choice_name) == 0:
                return CashFlow.RollConvention.UNADJUSTED
            if choice_name == "FOLLOWING":
                return CashFlow.RollConvention.FOLLOWING
            if choice_name == "MODIFIED_FOLLOWING":
                return CashFlow.RollConvention.MODIFIED_FOLLOWING
            if choice_name == "HALF_MONTH_MODIFIED_FOLLOWING":
                return CashFlow.RollConvention.HALF_MONTH_MODIFIED_FOLLOWING
            if choice_name == "PRECEDING":
                return CashFlow.RollConvention.PRECEDING
            if choice_name == "MODIFIED_PRECEDING":
                return CashFlow.RollConvention.MODIFIED_PRECEDING
            if choice_name == "NEAREST":
                return CashFlow.RollConvention.NEAREST
            raise NotImplementedError(f"unsupported roll convention: {choice_name}")

        @staticmethod
        def to_hdl_roll_convention(convention: 'CashFlow.RollConvention') -> RollConventionHDL:
            if convention is None:
                return RollConventionHDL.UNADJUSTED

            if convention == CashFlow.RollConvention.UNADJUSTED:
                return RollConventionHDL.UNADJUSTED
            if convention == CashFlow.RollConvention.FOLLOWING:
                return RollConventionHDL.FOLLOWING
            if convention == CashFlow.RollConvention.MODIFIED_FOLLOWING:
                return RollConventionHDL.MODIFIED_FOLLOWING
            if convention == CashFlow.RollConvention.HALF_MONTH_MODIFIED_FOLLOWING:
                return RollConventionHDL.HALF_MONTH_MODIFIED_FOLLOWING
            if convention == CashFlow.RollConvention.PRECEDING:
                return RollConventionHDL.PRECEDING
            if convention == CashFlow.RollConvention.MODIFIED_PRECEDING:
                return RollConventionHDL.MODIFIED_PRECEDING
            if convention == CashFlow.RollConvention.NEAREST:
                return RollConventionHDL.NEAREST
            raise NotImplementedError(f"unsupported roll convention: {convention}")

    class CashflowStatus(models.TextChoices):
        INACTIVE = "inactive", __("INACTIVE")

        # cashflow starts in this state
        DRAFT = "draft", __("DRAFT")

        # the cashflow moves in to this state from draft
        PENDING_ACTIVATION = "pending_activation", __("PENDING ACTIVATION")
        ACTIVE = "active", __("ACTIVE")
        PENDING_DEACTIVATION = "pending_deactivation", __("PENDING_DEACTIVATION")

    # ==================================================================
    #  Model data
    # ==================================================================

    # The pay date of the cashflow, when its received/paid
    date = models.DateTimeField()

    # Currency of the cashflow
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='%(class)s_currency', null=False)

    # Amount of the cashflow in its currency
    amount = models.FloatField(null=False)

    # Name of the cashflow
    name = models.CharField(max_length=60, null=True)

    # Description of the cashflow
    description = models.TextField(null=True, blank=True)

    # The periodicity of the cashflow. defined using icalendar format
    # see https://icalendar.org for more information
    periodicity = models.TextField(null=True, blank=True)

    # The calendar type of the cashflow
    calendar = models.CharField(max_length=64, choices=CalendarType.choices, default=CalendarType.NULL_CALENDAR,
                                null=True, blank=True)

    # The roll convention of the cashflow.
    roll_convention = models.CharField(max_length=64, choices=RollConvention.choices,
                                       default=RollConvention.UNADJUSTED, null=True, blank=True)

    # The end date if this is a recurring cashflow.
    end_date = models.DateTimeField(null=True, blank=True)

    # The cashflow can be part of an installment. If so (not null), this is the installment the cashflow belongs to.
    installment = models.ForeignKey(InstallmentCashflow, null=True, blank=True, on_delete=models.CASCADE)

    indicative_rate = models.FloatField(null=True, blank=True)

    indicative_base_amount = models.FloatField(null=True, blank=True)

    indicative_cntr_amount = models.FloatField(null=True, blank=True)

    booked_rate = models.FloatField(null=True, blank=True)

    booked_base_amount = models.FloatField(null=True, blank=True)

    booked_cntr_amount = models.FloatField(null=True, blank=True)

    # Return the next date for the recurrent cashflow
    @property
    def next_date(self):
        if self.periodicity:
            for dt in dateutil.rrule.rrulestr(self.periodicity, dtstart=self.date):
                if dt.date() >= date.today():
                    return dt.date()
            else:
                return None

        if self.installment_id:
            qs = self.installment.cashflow_set
            next_cf = qs.filter(date__gte=date.today()).order_by('date').first()
            if not next_cf:
                return None
            return next_cf.date.date()

        return None

    def __str__(self):
        return f"{self.name} ({self.id})"


class CashFlow(BaseCashFlow):
    """
    A cashflow generator object, this object defines how to generate one or more cashflows.
    """

    class Meta:
        verbose_name_plural = "cashflows"

    class CashflowStatus(models.TextChoices):
        INACTIVE = "inactive", __("INACTIVE")
        PENDING_APPROVAL = 'pending_approval', __("PENDING APPROVAL")
        PENDING_ACTIVATION = "pending_activation", __("PENDING ACTIVATION")
        ACTIVE = "active", __("ACTIVE")
        PENDING_DEACTIVATION = "pending_deactivation", __("PENDING DEACTIVATION")
        PENDING_MARGIN = "pending_margin", __("PENDING MARGIN")
        PENDING_PAYMENT = "pending_payment", __("PENDING PAYMENT")
        PAYMENT_FAIL = "payment_fail", __("PAYMENT FAIL")

    # The account to which this cashflow is tied
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='cf_account', null=False)

    status = models.CharField(max_length=24, default=CashflowStatus.PENDING_ACTIVATION, choices=CashflowStatus.choices)

    # The draft that gave rise to this cashflow.
    draft = models.ForeignKey('DraftCashFlow', null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='cf_draft')

    # The furthest date that a cashflow has been generated for this cashflow.
    # Any cashflows that have been generated before this date do not need to be regenerated.
    # Note that if the generator is modified, cashflows before this date will not be regenerated.
    # If the field is null, that means that no Parachute cashflows have been generated for this cashflow.
    # TODO: Once we make the Cashflows model the CashflowGenerator model, this field may need to be rethought.
    last_generated_point = models.DateTimeField(null=True, blank=True)

    def update_from_draft(self):
        if self.draft is None:
            return
        self.name = self.draft.name
        self.date = self.draft.date
        self.amount = self.draft.amount
        self.description = self.draft.description
        self.periodicity = self.draft.periodicity
        self.calendar = self.draft.calendar
        self.end_date = self.draft.end_date
        self.currency = self.draft.currency
        self.status = CashFlow.CashflowStatus.PENDING_ACTIVATION
        self.installment = self.draft.installment
        self.account = self.draft.account

    @property
    def is_draft(self) -> bool:
        return self.draft is not None

    @property
    def is_recurring(self) -> bool:
        return self.periodicity is not None and self.periodicity != ""

    def get_hdl_cashflows(self) -> Iterable[CashFlowHDL]:
        """
        Returns the cashflow as a list of CashFlowHDL objects
        """
        return get_hdl_cashflows(name=self.name, amount=self.amount,
                                 currency=self.currency,
                                 calendar=self.calendar,
                                 roll_convention=self.roll_convention,
                                 date=Date.from_datetime(self.date),
                                 end_date=Date.from_datetime(self.end_date) if self.end_date is not None else None,
                                 is_recurring=self.is_recurring,
                                 periodicity=self.periodicity)

    @staticmethod
    @get_or_none
    def get_cashflow(cashflow_id: int) -> 'CashFlow':
        return CashFlow.objects.get(pk=cashflow_id)

    @staticmethod
    @get_or_none
    def get_cashflows(cashflow_ids: Iterable[int]) -> Iterable['CashFlow']:
        return CashFlow.objects.filter(id__in=cashflow_ids)

    # ============================
    # Modifiers
    # ============================

    @staticmethod
    def create_cashflow(account: AccountTypes,
                        date: Date,
                        currency: CurrencyTypes,
                        amount: float,
                        status: CashflowStatus,
                        name: str = None,
                        description: str = None,
                        periodicity: str = None,
                        calendar: BaseCashFlow.CalendarType = BaseCashFlow.CalendarType.NULL_CALENDAR,
                        end_date: Date = None,
                        roll_convention: BaseCashFlow.RollConvention = None,
                        installment_id: Union[InstallmentCashflow, int] = None,
                        save: bool = True) -> 'CashFlow':

        """
        Create a cashflow in this account. Only allows currencies that are configured in the AccountCurrency to be
        added.

        :param account: int or Account, either the account or its id
        :param date: Date, when the cashflow occurs
        :param currency: int (currency_id), str (mnemonic, e.g. USD), or Currency
        :param amount: float, the amount of cashflow (+/-)
        :param status: CashflowStatus, the status of the cashflow
        :param name: str (optional),
        :param description: str, a description of the cashflow
        :param periodicity: str, the periodicity type of the cashflow. If this is none or empty, the cashflow is not
            a recurring cashflow
        :param calendar: CalendarType, specifies the calendar under which the cashflow or recurring cashflow will roll
        :param end_date: Date, the (optional) end date of a recurring cashflow
        :param roll_convention: RollConvention, the (optional) roll convention for the cashflow
        :param installment_id: int or InstallmentCashflow, the (optional) installment to which this cashflow belongs
        :param save: bool, if True, save the cashflow before returning it
        :return: Cashflow
        """
        account_ = Account.get_account(account=account)

        if not account_:
            raise Account.NotFound(account)

        cny = Currency.get_currency(currency)
        if not cny:
            raise Currency.NotFound(currency)

        if amount == 0:
            raise Exception(f"The cashflow amount cannot be zero")

        if installment_id:
            installment = InstallmentCashflow.get_installment(company_id=account_.company,
                                                              installment_id=installment_id)
            if not installment:
                raise InstallmentCashflow.NotFound(installment)
        else:
            installment = None

        date = Date.to_date(date)
        end_date = Date.to_date(end_date) if end_date else None
        cashflow = CashFlow(account=account_, date=date, currency=cny,
                            amount=amount, created=Date.now(), name=name, status=status, description=description,
                            periodicity=periodicity, calendar=calendar, end_date=end_date,
                            roll_convention=roll_convention, installment=installment)
        if save:
            cashflow.save()
        return cashflow

    @staticmethod
    def edit_cashflow(cashflow: 'CashFlow',
                      date: Date,
                      currency: CurrencyTypes,
                      amount: float,
                      status: CashflowStatus,
                      name: str = None,
                      description: str = None,
                      periodicity: str = None,
                      calendar: BaseCashFlow.CalendarType = BaseCashFlow.CalendarType.NULL_CALENDAR,
                      end_date: Date = None,
                      roll_convention: BaseCashFlow.RollConvention = BaseCashFlow.RollConvention.UNADJUSTED,
                      installment_id: Union[InstallmentCashflow, int] = None) -> 'CashFlow':

        """
        Update a cashflow, this creates a new version of the cashflow and
        sets the original status as PENDING_DEACTIVATION
        """

        cny = Currency.get_currency(currency)
        if not cny:
            raise Currency.NotFound(currency)

        if installment_id:
            installment = InstallmentCashflow.get_installment(company_id=cashflow.account.company,
                                                              installment_id=installment_id)
            if not installment:
                raise InstallmentCashflow.NotFound(installment)
        else:
            installment = None

        cashflow.currency = currency
        cashflow.date = date
        cashflow.amount = amount
        cashflow.status = status
        cashflow.name = name
        cashflow.description = description
        cashflow.periodicity = periodicity
        cashflow.calendar = calendar
        cashflow.end_date = end_date
        cashflow.roll_convention = roll_convention
        cashflow.installment = installment
        cashflow.save()
        return cashflow

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_company_cashflows(company: Company,
                              status: Optional['CashFlow.CashflowStatus'] = None) -> Iterable['CashFlow']:
        query_set = CashFlow.objects.filter(account__company=company)
        if status:
            return query_set.filter(status=status)
        else:
            return query_set

    @staticmethod
    def get_company_active_cashflows(company: Company, include_pending_margin: bool = False) -> Iterable['CashFlow']:
        if include_pending_margin:
            return CashFlow.objects.filter(account__company=company,
                                           status__in=[CashFlow.CashflowStatus.ACTIVE,
                                                       CashFlow.CashflowStatus.PENDING_ACTIVATION,
                                                       CashFlow.CashflowStatus.PENDING_MARGIN])
        else:
            return CashFlow.objects.filter(account__company=company,
                                           status__in=[CashFlow.CashflowStatus.ACTIVE,
                                                       CashFlow.CashflowStatus.PENDING_ACTIVATION])

    @staticmethod
    def get_company_pending_margin_cashflows(company: Company) -> Iterable['CashFlow']:
        return CashFlow.objects.filter(account__company=company,
                                       status__in=[CashFlow.CashflowStatus.PENDING_MARGIN])

    @staticmethod
    def get_cashflow_object(start_date: Date,
                            account: AccountTypes,
                            exclude_unknown_on_ref_date: bool = False,
                            currencies: Iterable[Union[CurrencyId, Currency]] = None,
                            include_pending_margin: bool = False) -> Iterable['CashFlow']:
        """
        Get "active" cashflows for an account, ie those that have not already been paid
        :param start_date: Date, the reference date (only cashflows occurring on or after this date are considered)
        :param account: AccountId or Account
        :param exclude_unknown_on_ref_date: bool, if true, exclude all cashflows that were not created by the ref_date,
            this flag is for historical testing / reporting purposes, since hedges only knew cashflows that existed
            at the time of the hedge
        :param currencies: Iterable of currency ids or objects (optional), if supplied only return matching currencies
        :param include_pending_margin: bool, if true, include cashflows with status PENDING_MARGIN
        :return: iterable of CashFlow objects
        """
        # TODO: Separate the date range, start_date, max_days_away, and the reference date, which is used to filter
        #   with created__lte.

        filters = {"account": account}

        if exclude_unknown_on_ref_date:
            filters["created__lte"] = start_date

        if currencies is not None:
            filters["currency__in"] = currencies

        filters['status__in'] = [CashFlow.CashflowStatus.ACTIVE, CashFlow.CashflowStatus.PENDING_ACTIVATION]
        if include_pending_margin:
            filters['status__in'].append(CashFlow.CashflowStatus.PENDING_MARGIN)

        return CashFlow.objects.filter(**filters).order_by('date')

    @staticmethod
    def get_active_cashflows(start_date: Date,
                             account: AccountTypes,
                             inclusive: bool = False,
                             include_end: bool = False,
                             max_days_away: Optional[int] = None,
                             max_date_in_future: Optional[Date] = None,
                             exclude_unknown_on_ref_date: bool = False,
                             currencies: Iterable[Union[CurrencyId, Currency]] = None,
                             include_pending_margin: bool = False,
                             skip_less_than_ref_date: bool = False
                             ) -> Iterable['CashFlowHDL']:
        """
        Get "active" cashflows for an account, ie those that have not already been paid
        :param start_date: Date, the reference date (only cashflows occurring on or after this date are considered)
        :param account: AccountId or Account
        :param inclusive: bool, if true, include cashflows occurring on exactly on the ref_date,
            else only those strictly after.
        :param include_end: bool, if true, include cashflows that occur exactly on the end_date, else only include
            those strictly before.
        :param max_days_away: int (optional), if supplied, ignore all cashflows that are more than this many
            days from the ref_date
        :param max_date_in_future: Date (optional), if supplied ignore all cashflows after this date
        :param exclude_unknown_on_ref_date: bool, if true, exclude all cashflows that were not created by the ref_date,
            this flag is for historical testing / reporting purposes, since hedges only knew cashflows that existed
            at the time of the hedge
        :param currencies: Iterable of currency ids or objects (optional), if supplied only return matching currencies
        :param include_pending_margin: bool, if true, include cashflows with status PENDING_MARGIN
        :param skip_less_than_ref_date: bool, if true, it will not return any cashflow if the created date is less than ref_date
        :return: iterable of CashFlow objects
        """
        cfs = CashFlow.get_cashflow_object(start_date=start_date,
                                           account=account,
                                           exclude_unknown_on_ref_date=exclude_unknown_on_ref_date,
                                           currencies=currencies,
                                           include_pending_margin=include_pending_margin)

        return iter_active_cashflows(cfs=cfs, ref_date=start_date,
                                     include_cashflows_on_vd=inclusive,
                                     include_end=include_end,
                                     max_days_away=max_days_away,
                                     max_date_in_future=max_date_in_future,
                                     skip_less_than_ref_date=skip_less_than_ref_date)

    @staticmethod
    def add_cashflow_to_installment(account: AccountTypes,
                                    installment_name: str,
                                    cashflow: 'CashFlow') -> 'CashFlow':
        """ Add a cashflow to an installment. """
        account = Account.get_account(account)
        if not account:
            raise Account.NotFound(account)
        with transaction.atomic():
            installment, _ = InstallmentCashflow.objects.get_or_create(account=account,
                                                                       installment_name=installment_name)
            installment.cashflow_set.add(cashflow)
            return cashflow

    @staticmethod
    def is_part_of_an_installment(cashflow: 'CashFlow') -> bool:
        """ Check if a cashflow is part of any installment series. """
        return cashflow.installment is not None

    @staticmethod
    def get_all_cashflow_currencies(account: AccountTypes) -> Set[Currency]:
        """ Get the currencies of all cashflows for an account. """
        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)

        currencies = set([])
        for cf in CashFlow.objects.filter(account=account_, status=CashFlow.CashflowStatus.ACTIVE):
            currencies.add(cf.currency)
        return currencies

    class NotFound(Exception):
        def __init__(self, account_id: AccountTypes, id: Union[int, 'CashFlow']):
            super(CashFlow.NotFound, self).__init__(f"CashFlow with id:{id} is not found for account {account_id}")

    @staticmethod
    def update_pending_cashflows(company: Company) -> List['CashFlow']:
        """
        Update all pending cashflows for a company, this will activate any pending cashflows that are due as
        well as deactivate any cashflows that are pending deactivation.
        Note that this method should be called from some service as part of EOD flow.
        :param company: Company
        """
        update_cashflows = []
        with transaction.atomic():
            for cf in CashFlow.get_company_cashflows(company=company,
                                                     status=CashFlow.CashflowStatus.PENDING_ACTIVATION):
                cf.status = CashFlow.CashflowStatus.ACTIVE
                cf.save()
                update_cashflows.append(cf)
            for cf in CashFlow.get_company_cashflows(company=company,
                                                     status=CashFlow.CashflowStatus.PENDING_DEACTIVATION):
                cf.status = CashFlow.CashflowStatus.INACTIVE
                cf.save()
                update_cashflows.append(cf)
            return update_cashflows


class DraftCashFlow(BaseCashFlow):
    class Action(models.TextChoices):
        CREATE = "CREATE"
        UPDATE = "UPDATE"
        DELETE = "DELETE"

    class Meta:
        verbose_name_plural = "drafts"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='draft_company', null=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='drafts', null=True, blank=True)

    # this field is used by the frontend team. It is used to store the action that is being performed on the cashflow.
    # It is used to allow the end user to draft-delete a cashflow for example.
    action = models.CharField(max_length=10, choices=Action.choices, null=False)

    def create_cashflow(self) -> CashFlow:
        return CashFlow.objects.create(name=self.name,
                                       date=self.date,
                                       amount=self.amount,
                                       description=self.description,
                                       periodicity=self.periodicity,
                                       calendar=self.calendar,
                                       end_date=self.end_date,
                                       currency=self.currency,
                                       status=CashFlow.CashflowStatus.PENDING_ACTIVATION,
                                       installment=self.installment,
                                       account=self.account,
                                       indicative_rate=self.indicative_rate,
                                       indicative_base_amount=self.indicative_base_amount,
                                       indicative_cntr_amount=self.indicative_cntr_amount)

    def to_cashflow(self) -> CashFlow:
        return CashFlow(name=self.name,
                        date=self.date,
                        amount=self.amount,
                        description=self.description,
                        periodicity=self.periodicity,
                        calendar=self.calendar,
                        end_date=self.end_date,
                        currency=self.currency,
                        status=CashFlow.CashflowStatus.PENDING_ACTIVATION,
                        installment=self.installment,
                        account=self.account)


class CashFlowNote(TimeStampedModel):
    cashflow = models.ForeignKey(CashFlow, on_delete=models.CASCADE, related_name='notes')
    created_by = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    modified_by = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    description = models.TextField()


auditlog.register(CashFlow)
auditlog.register(DraftCashFlow)
