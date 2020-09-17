""" {{ description }} """
import typing as t

from .client import AuthenticatedClient, Client
from .models.base_error import BaseError


def setup_from_token(token: str, host: str) -> AuthenticatedClient:
    return AuthenticatedClient(host, token)


def setup(username: str, password: str, host: str) -> t.Union[AuthenticatedClient, BaseError]:
    from .models.login_user_data import LoginUserData_1 as _LoginData
    client = Client(host)
    data = _LoginData(username=username, password=password)
    res = client.user.login(client=client, json_body=data)
    if isinstance(res, BaseError):
        return BaseError
    return AuthenticatedClient(host, res.access_token)
