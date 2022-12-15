from .utils import MockRequest, RequestModule


class UseTokenizedRequestsMixin:
    request: MockRequest

    @property
    def requests(self):
        return RequestModule(self.http_authorization)

    @property
    def http_authorization(self):
        return self.request.META.get("HTTP_AUTHORIZATION", "")
