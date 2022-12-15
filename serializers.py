from typing import TypedDict, Optional, Any
import functools
from rest_framework import serializers, exceptions

from .views import UseTokenizedRequestsMixin

from .utils import MockRequest
from .models import Image


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
        user_id = self.request.user.get("user_id") if self.request.user else None
        if not user_id:
            raise exceptions.PermissionDenied
        validated_data["user_id"] = user_id
        if func.__name__ == "create":
            instance = func(self, validated_data)
        else:
            obj = args[0]
            instance = func(self, obj, validated_data)
        return instance

    return wrapper


def ImageInjector(func):
    @functools.wraps(func)
    def wrapper(self, *args):
        validated_data = args[-1]
        image = validated_data.pop("image", None)
        user_id = self.context["request"].user.get("user_id")
        if func.__name__ == "create":
            instance = func(self, validated_data)
        else:
            obj = args[0]
            instance = func(self, obj, validated_data)

        if image:
            Image.create_single_instance(user_id, instance, image)
        return instance

    return wrapper
