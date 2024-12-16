from abc import ABC

from main.apps.cashflow.models import CashFlowGenerator, SingleCashFlow


class CashFlowGeneratorService(ABC):

    @staticmethod
    def generate_single_cashflow(generator: CashFlowGenerator):
        if generator.periodicity:
            occurrences = generator.periodicity.between(
                generator.periodicity_start_date,
                generator.periodicity_end_date,
                inc=True
            )
            for occurrence in occurrences:
                SingleCashFlow.objects.create(
                    company=generator.company,
                    generator=generator,
                    value_date=occurrence,
                    buy_currency=generator.buy_currency,
                    sell_currency=generator.sell_currency,
                    status=SingleCashFlow.Status.PENDING,
                    name=f"{generator.name} ({occurrence})",
                    description=f"{generator.description} ({occurrence})"
                )
        else:
            SingleCashFlow.objects.create(
                company=generator.company,
                generator=generator,
                value_date=generator.value_date,
                buy_currency=generator.buy_currency,
                sell_currency=generator.sell_currency,
                status=SingleCashFlow.Status.PENDING,
                name=generator.name,
                description=generator.description
            )
