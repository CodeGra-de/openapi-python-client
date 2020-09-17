from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Union, cast

import httpx

from ..errors import ApiResponseError
from ..utils import maybe_to_dict, response_code_matches, to_multipart, try_any

if TYPE_CHECKING:
    from ..client import AuthenticatedClient, Client

{% for relative in collection.relative_imports %}
{{ relative }}
{% endfor %}
{% for endpoint in collection.endpoints %}

{% from "endpoint_macros.pyi" import header_params, query_params, json_body, return_type %}

def {{ endpoint.name | snakecase }}(
    {% if endpoint.json_body %}
    json_body: {{ endpoint.json_body.get_type_string() }},
    {% endif %}
    {# Multipart data if any #}
    {% if endpoint.multipart_body_reference %}
    multipart_data: {{ endpoint.multipart_body_reference.class_name }},
    {% endif %}
    *,
    {# Proper client based on whether or not the endpoint requires authentication #}
    {% if endpoint.requires_security %}
    client: 'AuthenticatedClient',
    {% else %}
    client: 'Client',
    {% endif %}
    {# path parameters #}
    {% for parameter in endpoint.path_parameters %}
    {{ parameter.to_string() }},
    {% endfor %}
    {# Form data if any #}
    {% if endpoint.form_body_reference %}
    form_data: {{ endpoint.form_body_reference.class_name }},
    {% endif %}
    {# query parameters #}
    {% for parameter in endpoint.query_parameters %}
    {{ parameter.to_string() }},
    {% endfor %}
    {% for parameter in endpoint.header_parameters %}
    {{ parameter.to_string() }},
    {% endfor %}
    extra_parameters: Mapping[str, str] = None,
{{ return_type(endpoint) }}
    """ {{ endpoint.description }} """
    url = "{}{{ endpoint.path }}".format(
        client.base_url
        {%- for parameter in endpoint.path_parameters -%}
        ,{{parameter.name}}={{parameter.python_name}}
        {%- endfor -%}
    )

    headers: Dict[str, Any] = client.get_headers()
    {{ header_params(endpoint) | indent(4) }}

    {{ query_params(endpoint) | indent(4) }}
    if extra_parameters:
        params.update(extra_parameters)

    {{ json_body(endpoint) | indent(4) }}

    response = httpx.{{ endpoint.method }}(
        url=url,
        headers=headers,
        {% if endpoint.form_body_reference %}
        data=asdict(form_data),
        {% endif %}
        {% if endpoint.multipart_body_reference %}
        files=to_multipart(multipart_data.to_dict()),
        {% endif %}
        {% if endpoint.json_body %}
        json={{ "json_" + endpoint.json_body.python_name }},
        {% endif %}
        params=params,
    )

    {% for response in endpoint.responses %}
    if response_code_matches(response.status_code, {{ response.status_code }}):
        {% if response.is_error %}
        raise {{ response.constructor() }}
        {% else %}
        return {{ response.constructor() }}
        {% endif %}
    {% endfor %}
    else:
        raise ApiResponseError(response=response)
{% endfor %}
