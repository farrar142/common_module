from typing import Optional, Any
from rest_framework import viewsets
from typing import Any, Callable
from rest_framework import exceptions, viewsets

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


class DisallowEditOtherUsersResourceMixin(BaseMixin):
    """
    본인이 아닌 다른 유저의 리소스 업데이트를 제한합니다.
    """

    def get_current_user(self):
        return self.request.user

    def is_update_allowed(self, instance) -> bool:
        """
        리소스 소유자의 ID를 확인하여 업데이트 가능 여부를 반환합니다.
        """
        if not self.request.user:
            return False
        if not self.request.user["user_id"] != instance.user_id:
            return False
        return False

    def update(self, request, *args, **kwargs):
        if not self.is_update_allowed(self.get_object()):
            raise exceptions.PermissionDenied("Operation not permitted")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self.is_update_allowed(self.get_object()):
            raise exceptions.PermissionDenied("Operation not permitted")
        return super().destroy(request, *args, **kwargs)
