import functools
from pprint import pprint
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    List,
    Optional,
    Set,
    TypedDict,
    TypeVar,
    Generic,
    Protocol,
    Mapping,
    Union,
    Iterable,
    Type,
)
from django_redis.cache import RedisCache
from django.core.cache import BaseCache, cache as _cache
from django.db import models

from rest_framework.utils.serializer_helpers import ReturnDict

from common_module.authentications import Token

if TYPE_CHECKING:
    from common_module.models import CommonModel


# 타입 힌트용 래퍼 데코레이터
def cache_wrapper(func: Callable[..., Any]):
    class CacheOverride(BaseCache):
        def keys(self, lookup: str) -> list[str]:
            ...

        def delete_many(self, lookups: Iterable[str]) -> None:
            ...

    def helper(*args, **kwargs) -> CacheOverride:
        return func(*args, **kwargs)

    return helper


@cache_wrapper
def get_cache(cache: BaseCache):
    return cache


cache = get_cache(_cache)


class QueryBase(Protocol):
    pk: int


# T = TypeVar("T", bound=Union[Mapping[str, Any], QueryBase])
T = TypeVar("T", bound=QueryBase)
LT = TypeVar("LT", bound=List[QueryBase])


class CacheBase:
    def __init__(self, user_id: int, model_name: str):
        self.user_id = user_id
        self.model_name = model_name
        self.global_key = f"0/{model_name}/global"

    def add_global_keys(self, key: str) -> List[str]:
        # 글로벌 키스토어에 키 추가
        keys = self.get_global_keys()
        keys.append(key)
        listed = list(set(keys))
        cache.set(self.global_key, listed)

        return listed

    def get_global_keys(self):
        # 글로벌 키스토어의 모든 키 추가
        return cache.get(self.global_key, [])

    def purge_global_keys(self, key: str):
        # 글로벌 키스토어에 해당 키 삭제
        keys: list = self.get_global_keys()
        try:
            index = keys.index(key)
            try:
                keys.pop(index)
                cache.set(self.global_key, list(set(keys)))
                cache.delete(key)
                return True
            except:
                return False
        except:
            return False

    def key(self, kwargs: dict):
        _dict = {}
        translated: List[str] = []
        for k, v in kwargs.items():
            try:
                _dict[k] = str(v)
                translated.append(f"{k}={str(v)}")
            except:
                _dict[k] = v
        key = f"{self.user_id}:{self.model_name}:{''.join(translated)}"

        # if len(key.split("-")) >= 4:
        #     raise Exception
        return key

    def purge(self, **kwargs):
        # 캐시된 데이터를 지웁니다
        key = self.key(**kwargs)
        self.purge_global_keys(key)
        cache.delete(key)


class UseSingleCache(CacheBase, Generic[T]):
    def get(self, **kwargs) -> Optional[T]:
        key = self.key(kwargs)
        self.add_global_keys(key)
        return cache.get(key, None)

    def set(self, value: T, timeout: Optional[int] = None, **kwargs) -> T:
        # 모든 캐시 데이터를 오버라이드합니다
        key = self.key(kwargs)
        self.add_global_keys(key)
        cache.set(key, value=value, timeout=timeout)
        return value


class UseIterCache(UseSingleCache, Generic[T]):
    def get(self, **kwargs) -> Optional[Iterable[T]]:
        key = self.key(kwargs)
        self.add_global_keys(key)
        return cache.get(key, None)

    def set(
        self, value: Iterable[T], timeout: Optional[int] = None, **kwargs
    ) -> Iterable[T]:
        # 모든 캐시 데이터를 오버라이드합니다
        key = self.key(kwargs)
        self.add_global_keys(key)
        cache.set(key, value=value, timeout=timeout)
        return value

    def update(self, model: T, **kwargs):
        # 캐시된 데이터에서 특정 데이터를 업데이트합니다
        qs = self.get(**kwargs)
        qs_list: List[T] = []
        if qs:
            for q in qs:
                if q.pk == model.pk:  # type:ignore
                    qs_list.append(model)
                else:
                    qs_list.append(q)
            self.set(qs_list, **kwargs)
        return qs_list

    def pop(self, id: int, **kwargs):
        # 캐시된 데이터 내에서 특정 데이터를 지웁니다
        qs = self.get(**kwargs)
        qs_list: Iterable[T] = []
        if qs:
            for q in qs:
                if q.pk == id:  # type:ignore
                    pass
                else:
                    qs_list.append(q)
            self.set(qs_list, **kwargs)
        return qs_list
