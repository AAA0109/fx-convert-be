from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import reverse
from django.views.generic.edit import FormView, UpdateView

from main.apps.corpay.forms import ManualForm, FxForwardPositionForm
from main.apps.corpay.models import UpdateRequest
from main.apps.hedge.models import FxForwardPosition


class ForwardCreateView(PermissionRequiredMixin, FormView):
    """
    Handle Manual Request from outside platform
    Create: CF, Account, and FxForwardPosition
    """
    template_name = "corpay/forward_form.html"
    permission_required = 'corpay.edit_view'
    form_class = ManualForm

    def get_success_url(self):
        if back_url := self.request.GET.get('back_url'):
            return back_url

        return reverse('admin:index')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        initial = kwargs["initial"]

        updaterequest_id = self.kwargs.get('updaterequest_id')
        if updaterequest_id:
            instance = UpdateRequest.objects.get(pk=updaterequest_id)
            initial['company'] = instance.company
            if instance.ndf_request:
                initial['pair'] = instance.ndf_request.pair_id
                initial['amount'] = instance.ndf_request.amount
                initial['delivery_date'] = instance.ndf_request.delivery_date
            kwargs['instance'] = instance

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'back_url': self.request.GET.get('back_url'),
            'title': 'Add/Edit Fx Forward Position',
        })
        return context

    def form_valid(self, form: ManualForm):
        """If the form is valid, save the associated model."""
        form.save()
        return super().form_valid(form)


class ForwardView(PermissionRequiredMixin, UpdateView, FormView):
    template_name = "corpay/forward_form.html"
    permission_required = 'corpay.edit_view'
    form_class = FxForwardPositionForm
    model = FxForwardPosition

    def get_success_url(self):
        if back_url := self.request.GET.get('back_url'):
            return back_url

        return reverse('admin:index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'back_url': self.request.GET.get('back_url'),
            'title': 'Fx Forward Position',
        })
        return context

    def form_valid(self, form):
        if super().form_valid(form):
            form.save()

        return super().form_valid(form)
