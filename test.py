import os
import json
import requests
from dotenv import load_dotenv
from typing import Any, Callable, Literal

from django.http.response import HttpResponse

from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from rest_framework_simplejwt.tokens import RefreshToken

from .utils import ServerRequests

load_dotenv()


def request_wrapper(func: Callable[..., Any]):
    def helper(*args, **kwargs) -> HttpResponse:
        return func(*args, **kwargs)

    return helper


class Client(APIClient):
    admin_token: str
    normal_token: str

    def module_login(self, t: str):
        token = f"Bearer {t}"
        self.asset = ServerRequests(os.getenv("ASSET_SERVER", ""), token)

    def login(self):
        t = self.get_token("TEST_USER_EMAIL", "TEST_USER_PASSWORD")
        self.admin_token = t
        self.credentials(HTTP_AUTHORIZATION=f"Bearer {t}")
        self.module_login(t)

    def wrong_login(self):
        self.credentials(HTTP_AUTHORIZATION="Bearer dawdawdw")
        self.module_login("dawdawdw")

    def logout(self):
        print("log out!")
        self.credentials()
        self.module_login("")

    def get_token(
        self,
        user_type: Literal["TEST_USER_EMAIL"],
        pw_type: Literal["TEST_USER_PASSWORD"],
    ):
        email = os.getenv(user_type)
        password = os.getenv(pw_type)
        auth_server = os.getenv("AUTH_SERVER", "https://auth.honeycombpizza.link")
        resp = requests.post(
            f"{auth_server}/auth/token", json={"email": email, "password": password}
        )
        return resp.json().get("access")

    @request_wrapper
    def get(
        self, path, data=None, follow=False, content_type="application/json", **extra
    ):
        response = super(Client, self).get(path, data=data, **extra)
        return response

    @request_wrapper
    def post(
        self,
        path,
        data=None,
        format=None,
        content_type="application/json",
        follow=False,
        **extra,
    ):
        if content_type == "application/json":
            data = json.dumps(data)
        return super(Client, self).post(
            path, data, format, content_type, follow, **extra
        )

    @request_wrapper
    def patch(
        self,
        path,
        data=None,
        format=None,
        content_type="application/json",
        follow=False,
        **extra,
    ):
        if content_type == "application/json":
            data = json.dumps(data)
        return super(Client, self).patch(
            path,
            data,
            format,
            content_type,
            follow,
            **extra,
        )

    @request_wrapper
    def delete(
        self,
        path,
        data=None,
        format=None,
        content_type="application/json",
        follow=False,
        **extra,
    ):
        if content_type == "application/json":
            data = json.dumps(data)
        return super(Client, self).delete(
            path,
            data,
            format,
            content_type,
            follow,
            **extra,
        )


class TestCase(APITestCase):
    client: Client
    client_class = Client
