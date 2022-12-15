import os
import requests
from datetime import datetime
from calendar import timegm
from typing import Literal, TypedDict, Any

from django.utils.datastructures import MultiValueDict
from django.http.request import HttpRequest
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http.request import QueryDict, HttpRequest
from rest_framework.request import Request
from django.utils.timezone import is_naive, make_aware, utc
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()


class Token(TypedDict):
    token_type: Literal["refresh"]
    exp: str
    iat: int
    jti: str
    user_id: int
    role: list[Literal["staff", "creator"]]


class MockRequest(HttpRequest, Request):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "__default__"]
    user: Token | None
    data: MultiValueDict[str, Any]
    FILES: MultiValueDict[str, InMemoryUploadedFile]
    query_params: QueryDict


class ServerRequests:
    token: str

    def __init__(self, host: str, token: str):
        self.host = host
        self.token = token

    def get(self, url, params=None, **kwargs):
        return requests.get(
            self.host + url,
            params=params,
            headers={"Authorization": self.token},
            timeout=2,
            **kwargs,
        )

    def post(self, url, params=None, json=None, **kwargs):
        return requests.post(
            self.host + url,
            params=params,
            json=json,
            headers={"Authorization": self.token},
            **kwargs,
        )

    def patch(self, url, data=None, **kwargs):
        return requests.get(
            self.host + url, data=data, headers={"Authorization": self.token}, **kwargs
        )

    def delete(self, url, **kwargs):
        return requests.delete(self.host + url, **kwargs)


class RequestModule:
    auth: ServerRequests

    def __init__(self, token: str):
        AUTH_SERVER = os.getenv("AUTH_SERVER", "")
        self.auth = ServerRequests(AUTH_SERVER, token)
        ASSET_SERVER = os.getenv("ASSET_SERVER", "")
        self.assets = ServerRequests(ASSET_SERVER, token)

    def get_user(self, user_id: str | int) -> (int | Literal[False]):
        resp = self.auth.get(f"/users/{user_id}/")
        if resp.status_code is not 200:
            return False
        return resp.json().get("id")


def make_utc(dt):
    if settings.USE_TZ and is_naive(dt):
        return make_aware(dt, timezone=utc)

    return dt


def aware_utcnow():
    return make_utc(datetime.utcnow())


def datetime_to_epoch(dt):
    return timegm(dt.utctimetuple())


def datetime_from_epoch(ts):
    return make_utc(datetime.utcfromtimestamp(ts))
