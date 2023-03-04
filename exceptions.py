from rest_framework import exceptions


class ConflictException(exceptions.APIException):
    status_code = exceptions.status.HTTP_409_CONFLICT
    default_detail = {"not_implemented": ["정의되지 않은 오류입니다. 백엔드 개발자에게 에러내용을 추가해 달라고하세요"]}
