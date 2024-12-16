from django.urls import path, include

from main.apps.country.api.views import (
    CountryListApiView,
    CountryCurrencyApiView,
    CurrencyCountryApiView

)

app_name = 'country'


urlpatterns = [
    path('', CountryListApiView.as_view(), name='country-list'),
    path('country_code/<str:country_code>/',
         CountryCurrencyApiView.as_view(), name='country-currency'),
    path('mnemonic/<str:mnemonic>/',
         CurrencyCountryApiView.as_view(), name='currency-country')
]
