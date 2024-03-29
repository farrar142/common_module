from typing import TypeVar, TypedDict, Optional, Any
import functools
from rest_framework import serializers, exceptions
from django.db import models

from common_module.exceptions import ConflictException
from .views import UseTokenizedRequestsMixin

from .utils import MockRequest
from .models import CommonModel, Image

T = TypeVar("T", bound=CommonModel)


class MockSerializerMeta:
    fields: set[str]
    read_only_fields: set[str]
    model: type[models.Model]


class ContextType(TypedDict):
    view: UseTokenizedRequestsMixin
    request: MockRequest


class ContextMixin:
    """
    FooSerializer(instance,context=self.get_serializer_context())
                            해당 컨텍스트를 시리얼라이저 내에서 사용하게 해줌
                            이 시리얼라이저를 사용하는 뷰셋은 UseTokenizedRequestsMixin를
                            상속받아야됨.
    """

    Meta: MockSerializerMeta
    context: ContextType
    instance: Any
    validated_data: Optional[dict]

    @property
    def view(self):
        return self.context["view"]

    @property
    def request(self):
        return self.context["view"].request


class SerializerContext(TypedDict):
    request: MockRequest


class BaseSerializer(ContextMixin, serializers.ModelSerializer):
    context: SerializerContext


class ImageSerializer(BaseSerializer):
    class Meta:
        model = Image
        fields = ("url", "path")


def UserIdInjector(func):
    @functools.wraps(func)
    def wrapper(self: ContextMixin, *args):
        validated_data = args[-1]
        user_id = self.request.auth.get("user_id") if self.request.auth else None
        if not user_id:
            raise exceptions.NotAuthenticated
        validated_data["user"] = self.request.user
        print("in serializer")
        print(self.request.user, self.request.auth)
        instance = func(self, *args)
        print(f"{instance=}")
        return instance

    return wrapper


def ImageInjector(func):
    @functools.wraps(func)
    def wrapper(self, *args):
        validated_data = args[-1]
        image = validated_data.pop("image", None)
        user_id = self.context["request"].auth.get("user_id")
        if func.__name__ == "create":
            instance = func(self, validated_data)
        else:
            obj = args[0]
            instance = func(self, obj, validated_data)

        if image:
            Image.create_single_instance(user_id, instance, image)
        return instance

    return wrapper


def UpdateAvailableFields(fields: list[str]):
    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            serializer: ContextMixin = args[0]
            data: dict = args[-1]
            if not serializer.instance:
                return func(*args, **kwargs)
            target_fields = serializer.Meta.fields
            remove_fields = list(filter(lambda x: not fields.count(x), target_fields))
            filtered_Fields = [(x, data.pop(x, None)) for x in remove_fields]
            error_fields = list(filter(lambda x: x[1] != None, filtered_Fields))
            if len(error_fields) >= 1:
                raise exceptions.ValidationError(
                    detail={
                        serializer.instance.__class__.__name__: list(
                            map(lambda x: f"{x[0]} 필드는 업데이트 불가능합니다.", error_fields)
                        )
                    }
                )
            return func(*args, **kwargs)

        return inner

    return decorator


def ResourceOwnerCheck(resource: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            serializer: BaseSerializer = args[0]
            instance: CommonModel = args[1]
            validated_data: dict = args[-1]
            user = serializer.request.auth
            if not user:
                print("not login")
                raise exceptions.NotAuthenticated
            # 수정 일때
            if isinstance(instance, CommonModel):
                target: Optional[CommonModel] = getattr(instance, resource)
            # 데이터일때
            else:
                target = validated_data.get(resource, None)
            if not target:
                raise ConflictException(detail={resource: "수정하고자 하는 리소스에 해당 리소스가 없습니다"})
            if target.user.pk != user["user_id"]:
                raise ConflictException(detail={resource: ["해당 모델의 소유자가 아닙니다."]})
            instance = func(*args, **kwargs)
            return instance

        return wrapper

    return decorator
