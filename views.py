from typing import Any, Callable
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, AbstractUser

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


class DisallowEditOtherUsersResourceMixin(viewsets.ModelViewSet):
    """
    본인이 아닌 다른 유저의 리소스 업데이트를 제한합니다.
    """

    def get_current_user(self):
        return self.request.user

    def is_update_allowed(self, instance) -> bool:
        """
        리소스 소유자의 ID를 확인하여 업데이트 가능 여부를 반환합니다.
        """
        user: AbstractBaseUser | AnonymousUser = self.get_current_user()
        if isinstance(instance, AbstractUser):
            return instance.pk == user.pk
        elif getattr(instance, "user", None) is not None:
            return instance.user.pk == user.pk

        return False

    def update(self, request, *args, **kwargs):
        if not self.is_update_allowed(self.get_object()):
            raise exceptions.PermissionDenied("Operation not permitted")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self.is_update_allowed(self.get_object()):
            raise exceptions.PermissionDenied("Operation not permitted")
        return super().destroy(request, *args, **kwargs)


class DisallowEditOtherUsersResourceWithoutAdminMixin(
    DisallowEditOtherUsersResourceMixin
):
    """
    본인이 아닌 다른 유저의 리소스 업데이트를 제한합니다.
    """

    def is_update_allowed(self, instance) -> bool:
        """
        리소스 소유자의 ID를 확인하여 업데이트 가능 여부를 반환합니다.
        """
        user: AbstractBaseUser | AnonymousUser = self.get_current_user()
        if isinstance(user, AnonymousUser):
            return False
        if isinstance(user, AbstractUser) and user.is_staff:
            return True
        if isinstance(instance, AbstractUser):
            return instance.pk == user.pk
        elif getattr(instance, "user", None) is not None:
            return instance.user.pk == user.pk
        return False
