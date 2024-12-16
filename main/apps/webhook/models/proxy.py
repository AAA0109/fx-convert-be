from rest_framework.authtoken.models import TokenProxy as BaseTokenProxy


class Token(BaseTokenProxy):

    class Meta:
        proxy = True
