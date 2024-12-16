from django.views.generic import TemplateView
from hdlib.DateTime.Date import Date

from main.apps.account.models.company import Company
from main.apps.reports.services.risk import get_movement_warnings
from main.apps.risk_metric.services.market_risk_service import MarketRiskService


class CurrencyMovementReportView(TemplateView):
    template_name = 'reports/currency_movement_report.html'

    def get_context_data(self, **kwargs):
        companies = Company.objects.filter(status=Company.CompanyStatus.ACTIVE)
        company_id = self.request.GET.get('company_id')

        try:
            company_id = int(company_id)
            values = MarketRiskService.get_market_changes_for_company(Date.now(), company_id)
            lines = list(values.keys())
            lines.sort()
            columns = list(values[lines[0]].keys())
            warnings = get_movement_warnings(values, 'volatility/movement/threshold')
        except (ValueError, IndexError) as e:
            values = []
            lines = []
            columns = []
            warnings = []

        return {
            'title': 'Currency Movement Report',
            'values': values,
            'lines': lines,
            'columns': columns,
            'companies': companies,
            'company_id': company_id,
            'warnings': warnings,
        }
