import uuid

from django.db import models

from django.core.validators import MinLengthValidator
# from django.contrib.postgres.functions import RandomUUID

from main.apps.oems.backend.utils     import DateTimeEncoder
from main.apps.oems.models.extensions import DateTimeWithoutTZField, CurrentTimestampField

# ========

class Queue(models.Model):
	"""
		id          bigserial    PRIMARY KEY,
	  enqueued_at timestamp  NOT NULL DEFAULT current_timestamp,
	  dequeued_at timestamp,
	  action text,
	  source text,
	  topic       text         NOT NULL CHECK (length(topic) > 0),
	  uid         bigint,
	  data        jsonb        NOT NULL,
	  resp        jsonb
	);"""

	# IMPLIED? id = AutoBigInteger(primary_key=True)
	eid = models.UUIDField(primary_key=False, default=uuid.uuid4, null=False)
	enqueued_at = DateTimeWithoutTZField(auto_now_add=True, blank=True) # current_timestamp
	dequeued_at = DateTimeWithoutTZField(null=True, blank=True)
	action = models.TextField(null=True, blank=True)
	source = models.TextField(null=True, blank=True)
	topic = models.TextField(null=False, blank=True, validators=[MinLengthValidator(1, 'the field must not be empty')])
	uid = models.BigIntegerField(null=True, blank=True) # TODO: could FK to ticket.id and cascade delete
	data = models.JSONField(encoder=DateTimeEncoder, null=False, blank=True)
	resp = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)
	resp_at = DateTimeWithoutTZField(null=True, blank=True)
	