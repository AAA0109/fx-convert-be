from main.apps.country.models import Country as BaseCountry


class Country(BaseCountry):

    class Meta:
        proxy = True
        verbose_name_plural = 'Countries'
