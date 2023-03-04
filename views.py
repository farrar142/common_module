from typing import Optional, Any
from rest_framework import viewsets
from .utils import MockRequest, RequestModule


class UseTokenizedRequestsMixin:
    request: MockRequest

    @property
    def requests(self):
        return RequestModule(self.http_authorization)

    @property
    def http_authorization(self):
        return self.request.META.get("HTTP_AUTHORIZATION", "")


class BaseMixin(viewsets.ModelViewSet):
    request: MockRequest
    cached_instance: Optional[Any]

    def get_object(self):
        if self.cached_instance:
            return self.cached_instance
        self.cached_instance = super().get_object()
        return self.cached_instance
