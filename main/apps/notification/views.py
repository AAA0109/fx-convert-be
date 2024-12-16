import inspect
import typing
from typing import Type, Optional

from django.db.models.base import ModelBase
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.views.generic.base import View

from main.apps.account.models import Company
from main.apps.notification.services.email.templates import EMAIL_APP_TEMPLATE_MAP, BaseEmailTemplate


class EmailPreviewView(View):
    email_template_class: Optional[Type[BaseEmailTemplate]] = None
    email_template_instance: BaseEmailTemplate = None

    def get(self, request, *args, **kwargs):
        try:
            self._init_template_class()
        except Exception as e:
            return HttpResponseBadRequest(f'Error: {e}')

        format = request.GET.get('format', 'html')
        content = self.email_template_instance.render(format)
        if format == 'txt':
            content = f'<pre>{content}</pre>'

        return HttpResponse(content)

    def _init_template_class(self):
        app = self._get_app()
        template = self._get_template()
        try:
            self.email_template_class = EMAIL_APP_TEMPLATE_MAP[app][template]
            if app == 'billing':
                if template == 'invoice':
                    company_id = self.request.GET.get('company_id')
                    if company_id is None:
                        self.email_template_class = None
                    else:
                        company = Company.objects.get(pk=company_id)
                        self.email_template_instance = self.email_template_class(company=company)
            else:
                kwargs = {}
                params = dict(inspect.signature(self.email_template_class.__init__).parameters)
                for name, item in params.items():
                    if name == 'self':
                        continue

                    if name not in self.request.GET:
                        raise Exception(f'"{name}" is required to this preview, it can be blank in the GET')

                    if isinstance(item.annotation, ModelBase):  # if the param is a Model class
                        if val := self.request.GET[name]:  # if the param with same name exists and wasn't null
                            kwargs[name] = item.annotation.objects.get(pk=val)
                        else:
                            kwargs[name] = item.annotation.objects.last()  # try to pick the last
                            if not kwargs[name]:
                                msg = f"Couldn't fetch an record from {item.annotation.__name__}"
                                raise item.annotation.DoesNotExist(msg)

                    elif item.annotation in [str, int]:  # param is int or str
                        kwargs[name] = self.request.GET[name]  # just pick the param from query

                    elif type(item.annotation) is typing.GenericAlias:  # handle: list[object]
                        item = self.email_template_class.__init__.__annotations__[name]
                        if item.__origin__ == list:
                            val = self.request.GET[name]
                            target_cls = item.__args__[0]
                            kwargs[name] = target_cls.objects.filter(pk__in=val.split(','))

                self.email_template_instance = self.email_template_class(**kwargs)

        except KeyError as e:
            raise Exception(f'Key not found {e}')

    def _get_app(self):
        app = 'account'
        if self.request.GET.get('app'):
            app = self.request.GET.get('app')
        return app

    def _get_template(self):
        template = 'default'
        if self.request.GET.get('template'):
            template = self.request.GET.get('template')
        return template
