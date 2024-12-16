import pytest
from django.conf import settings

from main.apps.corpay.services.confirm_parse import *


@pytest.mark.parametrize(
    "file_name,urls", [
        ('email_body_confirm.html',
         ['https://onlinecrossborder.corpay.com/Orders/Confirmation?id=8921C966A4C2461F8B97CE22563E784C&lang=en-CA']),
        ('email_body_non_corpay.html', []),
    ]
)
def test_get_email_urls(file_name, urls):
    """
    Test of parser html content to extract corpay urls
    """
    with open(settings.BASE_DIR / f'apps/corpay/tests/assets/{file_name}', 'rb') as fp:
        html_content = fp.read()
    assert EmailConfirmService().get_email_urls(html_content) == urls


@pytest.mark.parametrize(
    "file_name,details", [
        ('confirms-fwd-drawdown.html',
         DealDetailVO(type='forward', deal_number='24589875', order_number='EFD363356', client_code='311786')),
        ('confirms-spot-deal.html', DealDetailVO(type='spot', deal_number='24687148', client_code='317385')),
        ('confirms-spot-deal2.html', DealDetailVO(type='spot', deal_number='ECMT6443', client_code='318459')),
    ]
)
def test_get_deal_detail(file_name, details):
    """
    Test of parser html content to extract corpay urls
    """
    with open(settings.BASE_DIR / f'apps/corpay/tests/assets/{file_name}', 'r') as fp:
        html_content = fp.read()
    assert EmailConfirmService().get_deal_detail(html_content) == details
