from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, resolve_url
from django.views.generic import TemplateView
from google_auth_oauthlib.flow import Flow

from main.apps.core.models import VendorOauth, Config


def index(request):
    return JsonResponse({
        "message": "Welcome to Pangea Prime API",
        "status": "success"
    })

@staff_member_required
def gmail_authenticate(request):
    back_url = resolve_url('admin:core_vendoroauth_changelist')
    flow = Flow.from_client_config(
        client_config=Config.get_config(path='vendor/google/gmail').value,
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
        redirect_uri=request.build_absolute_uri(resolve_url('main:account:gmail-authenticate'))
    )

    # If this is the user's first time authorizing, redirect them to Google's OAuth 2.0 server
    if 'code' not in request.GET:
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        request.session['state'] = state
        return redirect(authorization_url)
    else:
        # The user is redirected back from Google's OAuth 2.0 server with an authorization code
        flow.fetch_token(code=request.GET['code'])
        credentials = flow.credentials
        VendorOauth.objects.update_or_create(
            user=request.user,
            company=request.user.company,
            vendor=VendorOauth.Vendor.GOOGLE,
            defaults={
                'service': 'gmail',
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_expiry': credentials.expiry,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
            }
        )
        return redirect('/admin')  # TODO: add the correct response


class OauthConnectListView(PermissionRequiredMixin, TemplateView):
    """
    List the services user can authorize with Oauth
    """
    template_name = "core/oauth_list.html"
    permission_required = 'core.connect_oauth'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'back_url': self.request.GET.get('back_url') or
                        resolve_url('admin:core_vendoroauth_changelist'),
            'services': [
                {
                    'name': 'Google/Gmail',
                    'start_url': resolve_url('main:account:gmail-authenticate'),
                },
            ],
        })
        return context
