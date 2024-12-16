from django.db import models
from django_extensions.db.models import TimeStampedModel
from main.apps.account.models import Company

# ==========

class LifeCycleEvent(TimeStampedModel):

	class Meta:
		indexes = [
			models.Index(fields=['ticket_id']),
		]

	ticket_id = models.UUIDField(
		primary_key=False, null=False, editable=False
	)

	# Required Fields
	company = models.ForeignKey(
		Company, on_delete=models.SET_NULL, related_name="company_name", null=True, blank=True,
		help_text="Related company associated with the transaction."
	)

	trader = models.TextField(null=True, blank=True)
	market_name = models.TextField(null=True, blank=True)
	side = models.CharField(max_length=10, null=True, blank=True)

	cashflow_id = models.TextField(
		null=True, blank=True,
		help_text="Unique identifier for the cashflow. If cashflow_id is provided, required fields are not necessary as they will be filled in appropriately from the cashflow."
	)

	transaction_id = models.TextField(
		null=True, blank=True,
		help_text="Client-supplied unique identifier for the transaction."
	)

	transaction_group = models.TextField(
		null=True, blank=True,
		help_text="Client-supplied identifier to provide transaction grouping."
	)

	customer_id = models.TextField(
		null=True, blank=True,
		help_text="Identifier for the customer associated with the company for the transaction."
	)

	text = models.TextField(null=True, blank=True)


