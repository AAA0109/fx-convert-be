import unittest

from django.db.models.signals import post_save
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

import main.libs.pubsub.publisher as pubsub
from main.apps.account.models import User
from main.apps.account.signals.handlers import generate_user_activation_token_handler
from main.apps.currency.models import Currency


class UserTestCase(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        pubsub.init_null({})

    def setUp(self):
        _, self.usd = Currency.create_currency(symbol="$", mnemonic="USD", name="US Dollar")

    def test_create_user(self):
        response = self.client.post(reverse('main:account:user-list'), {
            'email': 'user@example.com',
            'password': '09asdlkjaklsjd',
            'confirm_password': '09asdlkjaklsjd',
            'first_name': 'John',
            'last_name': 'Doe',
            'timezone': 'US/Eastern',
            'phone': '+14087990011'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, 'user@example.com')

    def test_create_user_with_invalid_email(self):
        response = self.client.post(reverse('main:account:user-list'), {
            'email': 'invalid',
            'password': '09asdlkjaklsjd',
            'confirm_password': '09asdlkjaklsjd'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_create_user_with_duplicate_email(self):
        response = self.client.post(reverse('main:account:user-list'), {
            'email': 'user@example.com',
            'password': '09asdlkjaklsjd',
            'confirm_password': '09asdlkjaklsjd',
            'first_name': 'John',
            'last_name': 'Doe',
            'timezone': 'US/Eastern',
            'phone': '+14087990011'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(reverse('main:account:user-list'), {
            'email': 'user@example.com',
            'password': '09asdlkjaklsjd',
            'confirm_password': '09asdlkjaklsjd',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'timezone': 'US/Eastern',
            'phone': '+14087990011'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_with_invalid_password(self):
        response = self.client.post(reverse('main:account:user-list'), {
            'email': 'invalid',
            'password': '09asdlkjaklsjd',
            'confirm_password': '09ASDLKJAKLSJD',
            'timezone': 'US/Eastern',
            'phone': '+14087990011'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_user_authentication(self):
        response = self.client.post(reverse('main:account:user-list'), {
            'email': 'user@example.com',
            'password': '09asdlkjaklsjd',
            'confirm_password': '09asdlkjaklsjd',
            'first_name': 'John',
            'last_name': 'Doe',
            'timezone': 'US/Eastern',
            'phone': '+14087990011'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(reverse('main:account:user-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # now authenticate with the wrong password and try again we should still get a 403
        response = self.login_jwt(email="user@example.com", password="wrong password")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_user(self):
        response = self.client.post(reverse('main:account:user-list'), {
            'email': 'user@example.com',
            'password': '09asdlkjaklsjd',
            'confirm_password': '09asdlkjaklsjd',
            'first_name': 'John',
            'last_name': 'Doe',
            'timezone': 'US/Eastern',
            'phone': '+14087990011'
        })
        user_id = response.data['id']
        user = User.objects.get(pk=user_id)
        user.is_active = True
        user.save()
        self.login_jwt(email="user@example.com", password="09asdlkjaklsjd")

        response = self.client.get(reverse('main:account:user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response_data = response.data[0]
        self.assertEqual(response_data['id'], user_id)
        self.assertEqual(response_data['email'], 'user@example.com')
        self.assertEqual(response_data['first_name'], 'John')
        self.assertEqual(response_data['last_name'], 'Doe')
        self.assertEqual(response_data['phone'], '+14087990011')

    def test_user_activation(self):
        post_save.connect(receiver=generate_user_activation_token_handler, sender=User)
        # create user
        response = self.client.post(reverse('main:account:user-list'), {
            'email': 'user@example.com',
            'password': '09asdlkjaklsjd',
            'confirm_password': '09asdlkjaklsjd',
            'first_name': 'John',
            'last_name': 'Doe',
            'timezone': 'US/Eastern',
            'phone': '+14087990011'
        })

        user_id = response.data['id']
        user = User.objects.get(pk=user_id)
        # assert is_active is false
        self.assertFalse(user.is_active)
        # test activation
        activation_token = user.activation_token
        response = self.client.get(
            reverse('main:account:activate-user'),
            data={
                'token': activation_token
            }
        )
        self.assertTrue(response.data['status'])
        post_save.disconnect(receiver=generate_user_activation_token_handler, sender=User)

    def login_jwt(self, email, password):
        token_url = reverse('main:auth:token_obtain_pair')
        response = self.client.post(token_url, {
            "email": email,
            "password": password
        }, format="json")
        if response.status_code == status.HTTP_200_OK:
            token = response.json()
            self.access_token = token['access']
            self.refresh_token = token['refresh']
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        return response


if __name__ == '__main__':
    unittest.main()
