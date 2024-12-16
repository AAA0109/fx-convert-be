from django import forms
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django_admin_inline_paginator.admin import TabularInlinePaginated

from .models import CollectorConfig
from .models.collector_config import StorageConfig
from .models.dataprovider import DataProvider
from .models.file import File
from .models.mapping import Mapping
from .models.profile import Profile, ProfileParallelOption
from .models.source import Source
from .models.value import Value


class ValueAdmin(admin.ModelAdmin):
    list_display = (
        'mapping', 'mapping_type', 'from_value', 'to_value',
        'to_currency', 'to_fxpair', 'data_provider', 'source', 'profile'
    )

    autocomplete_fields = ['to_fxpair']

    def data_provider(self, obj):
        if obj.mapping.profile:
            return obj.mapping.profile.source.data_provider.__str__()
        if obj.mapping.data_provider:
            return obj.mapping.data_provider.__str__()

    def source(self, obj):
        if obj.mapping.profile:
            return obj.mapping.profile.source.__str__()

    def profile(self, obj):
        return obj.mapping.profile.__str__()

    def mapping(self, obj):
        return obj.mapping.__str__()

    class Media:
        js = (
            'admin/js/value.js',  # value admin
        )


class ValueInLine(admin.TabularInline):
    model = Value
    extra = 0
    show_change_link = True


class MappingAdmin(admin.ModelAdmin):
    inlines = [
        ValueInLine
    ]
    list_display = ('column_name', 'data_provider', 'source', 'profile')

    def data_provider(self, obj):
        if hasattr(obj.profile, 'source'):
            return obj.profile.source.data_provider.__str__()
        if hasattr(obj.profile, 'data_provider'):
            return obj.profile.data_provider.__str__()

    def source(self, obj):
        if hasattr(obj.profile, 'source'):
            return obj.profile.source.__str__()

    def profile(self, obj):
        return obj.profile.__str__()

    class Media:
        js = (
            'admin/js/mapping.js',  # value admin
        )


class ProfileMappingInLine(admin.TabularInline):
    model = Mapping
    extra = 0
    show_change_link = True
    exclude = ('data_provider',)


class FileInline(TabularInlinePaginated):
    model = File
    extra = 0
    per_page = 10
    show_change_link = True
    can_delete = True
    filter = ['status']


class DataProviderMappingInLine(admin.TabularInline):
    model = Mapping
    extra = 0
    show_change_link = True
    exclude = ('profile',)


class ProfileParallelOptionInline(admin.TabularInline):
    model = ProfileParallelOption
    extra = 0


class ProfileAdmin(admin.ModelAdmin):
    TARGETS = [
        'marketdata',
        'hedge',
        'margin',
        'corpay',
        'ibkr',
        'country',
        'ndl',
        'currency'
    ]
    inlines = [
        ProfileParallelOptionInline,
        ProfileMappingInLine,
        FileInline,
    ]
    list_display = ('id', 'name', 'data_provider', 'source')
    list_filter = ('source__data_provider', 'source')

    def data_provider(self, obj):
        return obj.source.data_provider.__str__()

    def source(self, obj):
        return obj.source.__str__()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "target":
            kwargs["queryset"] = ContentType.objects.filter(app_label__in=self.TARGETS)
        return super(ProfileAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class ProfileInLine(admin.TabularInline):
    model = Profile
    extra = 0
    show_change_link = True
    fields = ('name', 'source', 'url', 'filename', 'directory', 'file_format', 'enabled', 'target',
              'data_cut_type')
    readonly_fields = ('id',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "target":
            kwargs["queryset"] = ContentType.objects.filter(app_label__in=ProfileAdmin.TARGETS)
        return super(ProfileInLine, self).formfield_for_foreignkey(db_field, request, **kwargs)


class SourceAdmin(admin.ModelAdmin):
    inlines = [
        ProfileInLine,
        FileInline
    ]
    list_display = ('name', 'data_provider')

    def data_provider(self, obj):
        return obj.data_provider.__str__()


class SourceInLine(admin.TabularInline):
    model = Source
    extra = 0
    show_change_link = True


class DataProviderForm(forms.ModelForm):
    class Meta:
        widgets = {
            'sftp_password': forms.PasswordInput(render_value=True)
        }

    class Media:
        js = (
            'admin/js/data_provider.js',
        )


class DataProviderAdmin(admin.ModelAdmin):
    form = DataProviderForm
    inlines = [
        SourceInLine,
        DataProviderMappingInLine,
        FileInline
    ]


class CollectorConfigInline(admin.TabularInline):
    model = CollectorConfig
    extra = 0
    show_change_link = True


class CollectorConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'collector', 'storage_config')
    list_filter = ('active',)
    search_fields = ('name', 'collector')
    ordering = ('name',)
    raw_id_fields = ('storage_config',)
    fieldsets = (
        (None, {
            'fields': ('name', 'active', 'collector', 'storage_config', 'kwargs')
        }),
    )


class StorageConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'writer', 'publisher', 'cache')
    search_fields = ('name',)
    inlines = [CollectorConfigInline]


# Register your models here.
admin.site.register(DataProvider, DataProviderAdmin)
admin.site.register(Source, SourceAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Mapping, MappingAdmin)
admin.site.register(Value, ValueAdmin)
admin.site.register(CollectorConfig, CollectorConfigAdmin)
admin.site.register(StorageConfig, StorageConfigAdmin)
