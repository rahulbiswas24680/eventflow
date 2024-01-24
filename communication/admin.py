from django.contrib import admin
from django.apps import apps

app_config = apps.get_app_config('communication')
admin.site.register(app_config.get_models())