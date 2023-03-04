# from django.contrib.auth.models import AnonymousUser
from typing import Literal, Any
from django.http.request import HttpRequest
from django.utils.datastructures import MultiValueDict
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import permissions
from rest_framework.request import Request, QueryDict

from common_module.utils import Token

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


class MockRequest(HttpRequest, Request):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "__default__"]
    user: Token | None
    data: MultiValueDict[str, Any]
    FILES: MultiValueDict[str, InMemoryUploadedFile]
    query_params: QueryDict


class EditAuthorOnly(permissions.BasePermission):
    request: MockRequest

    def has_object_permission(self, request: MockRequest, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user == None:
            return False
        if obj.user_id == request.user.get("user_id"):
            return True
        return False


class IsAuthenticated:
    request: MockRequest

    def has_permission(self, request: MockRequest, view):
        if request.user == None:
            return False
        return True

    def has_object_permission(self, request: MockRequest, view, obj):
        if request.user == None:
            return False
        if obj.user_id == request.user.get("user_id"):
            return True
        return False


class IsAdminUser:
    def has_permission(self, request: MockRequest, view):
        if request.user == None:
            return False
        # if obj.user_id == request.user.get("id"):
        #     return True
        elif request.user.get("role") and "staff" in request.user.get("role"):
            return True
        return False

    def has_object_permission(self, request: MockRequest, view, obj):
        if request.user == None:
            return False
        # if obj.user_id == request.user.get("id"):
        #     return True
        elif request.user.get("role") and "staff" in request.user.get("role"):
            return True
        return False


class AdminOrCreator(permissions.BasePermission):
    """
    Allows access only to admin users.
    """

    def has_permission(self, request: MockRequest, view):
        if request.user == None:
            return False
        role = request.user.get("role")
        if not role:
            return False
        return any(["staff" in role, "creator" in role])


# class IsFollowerOrAuthorReadOnly(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return request.user and request.user.is_authenticated

#     def has_object_permission(self, request, view, obj):
#         if obj.user == request.user:
#             return True

#         if obj.public_type == 0:
#             return True

#         if obj.public_type == 1:
#             activity_user = obj.user
#             if Relationship.objects.filter(user_from_id=request.user.id, user_to_id=activity_user.id).exists():
#                 return True

#         return False
