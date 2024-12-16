from typing import Optional

from auditlog.registry import auditlog
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from timezone_field import TimeZoneField

from main.apps.account.models.account import Account
from main.apps.account.models.company import Company
from main.apps.account.signals import activation_token_created
from main.apps.core.auth.tokens import account_activation_token_generator


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(email__iexact=username)

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    username = None
    email = models.EmailField(_('email address'), blank=True, unique=True)
    phone = PhoneNumberField(null=True, blank=True)
    timezone = TimeZoneField(default='UTC', null=True, blank=True)
    activation_token = models.CharField(max_length=60, null=True, blank=True)
    hs_contact_id = models.BigIntegerField(null=True, blank=True)
    phone_confirmed = models.BooleanField(null=False, default=False)
    phone_otp_code = models.CharField(max_length=6, null=True, blank=True)
    is_invited = models.BooleanField(null=False, default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class UserGroups(models.TextChoices):
        ADMIN_CUSTOMER_SUCCESS = 'admin_customer-success', 'Admin - Customer Success'
        ADMIN_READ_ONLY = 'admin_read-only', 'Admin - Read-only'
        CUSTOMER_ADMIN = 'customer_admin', 'Customer - Admin'
        CUSTOMER_CREATOR = 'customer_creator', 'Customer - Creator'
        CUSTOMER_MANAGER = 'customer_manager', 'Customer - Manager'
        CUSTOMER_VIEWER = 'customer_viewer', 'Customer - Viewer'
        CUSTOMER_CORPAY = 'customer_corpay', 'Customer - CorPay'
        CUSTOMER_IBKR = 'customer_ibkr', 'Customer - IBKR'
        ADMIN_GROUP = 'admin_group', 'Group - Admin'
        ACCOUNT_OWNER_GROUP = 'account_owner_group', 'Group - Account Owner'
        MANAGER_GROUP = 'manager_group', 'Group - Manager'


    class AlreadyExists(Exception):
        def __init__(self, email):
            super(User.AlreadyExists, self).__init__(f"User with email:{email} already exists")

    class NotFound(Exception):
        def __init__(self, user_id):
            super(User.NotFound, self).__init__(f"User with id:{user_id} does not exists")

    @staticmethod
    def generate_activation_token(user: 'User') -> Optional[str]:
        if user.is_active:
            return None
        activation_token = account_activation_token_generator.make_token(user)
        user.activation_token = activation_token
        user.save()
        if not user.is_invited:
            activation_token_created.send(sender=user.__class__, instance=user, activation_token=activation_token)
        return user.activation_token

    @property
    def phone_number(self):
        if self.phone is None:
            return None
        return self.phone.as_e164

    @staticmethod
    def get_user_by_email(email: str):
        return User.objects.get(email__exact=email)

    def save(self, *args, **kwargs):
        # Check if the company is changing
        if self.pk:
            old_instance = User.objects.get(pk=self.pk)
            if old_instance.company != self.company:
                kwargs['update_fields'] = kwargs.get('update_fields', None) or []
                if 'company' not in kwargs['update_fields']:
                    kwargs['update_fields'].append('company')
        super().save(*args, **kwargs)


auditlog.register(User)
