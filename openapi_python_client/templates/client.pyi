from dataclasses import dataclass
from functools import partial, wraps
from typing import Any, Dict, Union

{% for tag, collection  in all_collections.items() %}
{% set snake_tag = tag | snake_case %}
class _{{ tag }}Module:
    def __init__(self, client: 'Client') -> None:
        import {{ package_name }}.api.{{ snake_tag }} as {{ snake_tag }}

        {% for endpoint in collection.endpoints %}
        self.{{ endpoint.name }} = wraps({{ snake_tag}}.{{ endpoint.name }})(partial({{ snake_tag }}.{{ endpoint.name }}, client=client))
        {% endfor %}
{% endfor %}


@dataclass
class Client:
    """ A class for keeping track of data related to the API """

    base_url: str

    def get_headers(self) -> Dict[str, str]:
        """ Get headers to be used in all endpoints """
        return {}

    {% for tag in all_collections.keys() %}
    {% set snake_tag = tag | snake_case %}
    @property
    def {{ snake_tag }}(self) -> _{{ tag }}Module:
        return _{{ tag }}Module(self)
    {% endfor %}


@dataclass
class AuthenticatedClient(Client):
    """ A Client which has been authenticated for use on secured endpoints """

    token: str

    def get_headers(self) -> Dict[str, str]:
        """ Get headers to be used in authenticated endpoints """
        return {"Authorization": f"Bearer {self.token}"}
