from drf_spectacular.utils import extend_schema, inline_serializer
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.generators import SchemaGenerator
from rest_framework.permissions import IsAuthenticated

class CustomSchemaGenerator(SchemaGenerator):
    def get_endpoints(self, request):
        endpoints = super().get_endpoints(request)
        print(endpoints)
        # Remove authentication endpoints if the user is authenticated
        if request.user and request.user.is_authenticated:
            endpoints = [endpoint for endpoint in endpoints if 'auth' not in endpoint[0]]

        return endpoints

@extend_schema()
def custom_schema(request):
    from .urls import urlpatterns
    generator = CustomSchemaGenerator(
        patterns=urlpatterns,
        request=request,
        public=request.user.is_anonymous,
    )
    return generator.get_schema(request)
