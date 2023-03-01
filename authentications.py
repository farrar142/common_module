from dataclasses import dataclass, field
import os
import requests
import jwt
from dotenv import load_dotenv
from typing import Optional, Literal, TypedDict, Mapping
from django.http import HttpRequest

# from django.contrib.auth.models import AnonymousUser

from rest_framework import authentication, exceptions
from rest_framework.request import Request

from common_module.utils import aware_utcnow, datetime_from_epoch

load_dotenv()


@dataclass
class Token:
    exp: str
    iat: int
    jti: str
    user_id: int
    token_type: Literal["refresh", "access"] = "access"
    role: list[Literal["staff", "creator"]] = field(default_factory=list)

    def __getitem__(self, key: str, default=None):
        return getattr(self, key, default)

    def get(self, key: str, default=None):
        return self.__getitem__(key, default)

    @classmethod
    def make_user_token(cls, user_id: int):
        return Token(exp="", iat=0, jti="", user_id=user_id)


def get_jwt_token_from_dict(data: dict):
    bearer_token: Optional[str] = data.get("HTTP_AUTHORIZATION")
    if not bearer_token:
        return False
    splitted = bearer_token.split(" ")
    if not len(splitted) == 2:
        return False
    if splitted[0] != "Bearer":
        return False
    return splitted[1]


def parse_jwt(access_token: str) -> Token:
    try:
        token = jwt.decode(access_token, options={"verify_signature": False})
        return Token(**token)
    except:
        raise exceptions.NotAuthenticated


class ThirdPartyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request: HttpRequest):
        http_authorization = request.META.get("HTTP_AUTHORIZATION", "")
        resp = requests.post(
            os.getenv("AUTH_SERVER", "") + "/users/authenticate/",
            headers={"Authorization": http_authorization},
            timeout=5,
        )
        if resp.status_code != 200:
            raise exceptions.AuthenticationFailed("No such user")
        user: Token = resp.json()

        return (user, None)  # authentication successful


class InternalJWTAuthentication(authentication.BaseAuthentication):
    def check_exp(self, payload: Token, claim="exp", current_time=None):
        if current_time is None:
            current_time = aware_utcnow()
        try:
            claim_value = payload[claim]
        except:
            raise exceptions.NotAuthenticated
        claim_time = datetime_from_epoch(claim_value)
        if claim_time <= current_time:
            raise exceptions.NotAuthenticated

    def authenticate(self, request: HttpRequest):
        jwt = get_jwt_token_from_dict(request.META)
        if not jwt:
            return (None, None)
        parsed = parse_jwt(jwt)
        self.check_exp(parsed)
        return (parsed, None)
