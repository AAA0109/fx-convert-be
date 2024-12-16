from django.db import models


class VendorOauth(models.Model):
    company = models.ForeignKey("account.Company", on_delete=models.CASCADE)
    user = models.ForeignKey("account.User", on_delete=models.CASCADE)

    class Vendor(models.TextChoices):
        GOOGLE = 'GOOGLE'

    vendor = models.CharField(null=False, default=Vendor.GOOGLE, choices=Vendor.choices)
    service = models.CharField(max_length=100)
    token_uri = models.CharField(max_length=2048)
    access_token = models.CharField(max_length=250)
    refresh_token = models.CharField(max_length=250)
    client_id = models.CharField(max_length=80)
    client_secret = models.CharField(max_length=40)
    scopes = models.JSONField()
    token_expiry = models.DateTimeField()

    def __str__(self):
        return f"{self.company}: {self.vendor}-{self.service}"

