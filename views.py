from typing import Generic, Iterable, Optional, Any, TypeVar
from rest_framework import viewsets
from typing import Any, Callable
from django.db.models import QuerySet

from rest_framework import exceptions, viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from common_module.models import CommonModel

from .utils import MockRequest, RequestModule

T = TypeVar("T", bound=CommonModel)


class UseTokenizedRequestsMixin:
    request: MockRequest

    @property
    def requests(self):
        return RequestModule(self.http_authorization)

    @property
    def http_authorization(self):
        return self.request.META.get("HTTP_AUTHORIZATION", "")


class BaseMixinWrapper(viewsets.ModelViewSet, Generic[T]):
    request: MockRequest
    cached_instance: Optional[T] = None
    queryset: QuerySet[T]
    kwargs: dict
    filterset_fields: Iterable[str]

    def get_object(self) -> T:
        if self.cached_instance:
            return self.cached_instance
        self.cached_instance = super().get_object()
        return self.cached_instance

    def get_queryset(self) -> QuerySet[T]:
        return super().get_queryset()

    def filter_queryset(self, queryset) -> QuerySet[T]:
        return super().filter_queryset(queryset)

    def get_serializer_class(self) -> serializers.Serializer:
        return super().get_serializer_class()

    def get_serializer(self, *args, **kwargs) -> serializers.Serializer:
        return super().get_serializer(*args, **kwargs)


class BaseMixin(BaseMixinWrapper[T]):
    @action(methods=["GET"], detail=False, url_path="count")
    def count_resources(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(data={"count": queryset.count()})

    @action(methods=["GET"], detail=False, url_path="flat")
    def not_paginated(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        limit = self.request.query_params.get("limit")
        if limit and limit.isdigit():
            queryset = queryset[: int(limit)]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["GET"], detail=False, url_path="me")
    def my_resources(self, request, *args, **kwargs):
        if not self.request.user:
            raise exceptions.NotAuthenticated
        user_id = self.request.user.get("user_id")
        queryset = self.filter_queryset(self.get_queryset().filter(user_id=user_id))

        page = self.paginate_queryset(queryset)
        if page != None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["POST"], detail=False, url_path="bulk")
    def create_bulk(self, request, *args, **kwargs):
        _kwargs = {"many": isinstance(request.data, list)}
        serializer = self.get_serializer(data=request.data, **_kwargs)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class DisallowEditOtherUsersResourceMixin(BaseMixin[T]):
    """
    본인이 아닌 다른 유저의 리소스 업데이트를 제한합니다.
    """

    def get_current_user(self):
        return self.request.user

    def is_update_allowed(self, instance: T) -> bool:
        """
        리소스 소유자의 ID를 확인하여 업데이트 가능 여부를 반환합니다.
        """
        if not self.request.user:
            return False
        if not self.request.user["user_id"] == instance.user_id:
            return False
        return True

    def update(self, request, *args, **kwargs):
        if not self.is_update_allowed(self.get_object()):
            raise exceptions.PermissionDenied("Operation not permitted")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self.is_update_allowed(self.get_object()):
            raise exceptions.PermissionDenied("Operation not permitted")
        return super().destroy(request, *args, **kwargs)
