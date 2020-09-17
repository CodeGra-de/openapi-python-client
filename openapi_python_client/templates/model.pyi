from __future__ import annotations

import json
from dataclasses import dataclass
from io import StringIO
from typing import Any, Dict, Optional

from ..utils import maybe_to_dict
from .types import File

{% for relative in model.relative_imports %}
{% if relative != "from ." + model.reference.module_name + " import " + model.reference.class_name %}
{{ relative }}
{% endif %}
{% endfor %}

{% macro make_model(model) %}
@dataclass
class {{ model.reference.class_name }}{% if model.inherits -%}(
        {{ model.inherits.class_name }}
)
{%- elif model.is_error %}
(
    Exception
)
{%- endif -%}:
    """ {{ model.description }} """
    {% for property in model.required_properties + model.optional_properties %}
    {{ property.to_string() }}
    {% endfor %}

    raw_data: Optional[Dict[str, Any]] = None

    {% if model.is_error %}
    def __str__(self) -> str:
        return repr(self)
    {% endif %}

    def to_dict(self) -> Dict[str, Any]:
        {% if model.inherits %}
        res = super().to_dict()
        {% else %}
        res: Dict[str, Any] = {}
        {% endif %}

        {% for property in model.required_properties + model.optional_properties %}
        {% if property.template %}
        {% from "property_templates/" + property.template import transform %}
        {{ transform(property, "self." + property.python_name, property.python_name) | indent(8) }}
        {% else %}
        {{ property.python_name }} =  self.{{ property.python_name }}
        {% endif %}
        {% if property.required %}
        res["{{ property.name }}"] = {{ property.python_name }}
        {% else %}
        if self.{{ property.python_name }} is not None:
            res["{{ property.name }}"] = {{ property.python_name }}
        {% endif %}
        {% endfor %}

        return res

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> {{ model.reference.class_name }}:
{% if model.inherits %}
        base = {{ model.inherits.class_name }}.from_dict(d).to_dict()
{% else %}
        base = {}
{% endif %}
{% for property in model.required_properties + model.optional_properties %}
    {% if property.required %}
        {% set property_source = 'd["' + property.name + '"]' %}
    {% else %}
        {% set property_source = 'd.get("' + property.name + '")' %}
    {% endif %}
    {% if property.template %}
        {% from "property_templates/" + property.template import construct %}
        {{ construct(property, property_source) | indent(8) }}
    {% else %}
        {{ property.python_name }} = {{ property_source }}
    {% endif %}

{% endfor %}
        return {{ model.reference.class_name }}(
            **base,
{% for property in model.required_properties + model.optional_properties %}
            {{ property.python_name }}={{ property.python_name }},
{% endfor %}
            raw_data=d,
        )
{% endmacro %}

{% if model.is_union %}
from typing import Union

{% for submodel in model.joins %}
{{ make_model(submodel) }}
{% endfor %}
{{ model.reference.class_name }} = Union[{% for submodel in model.joins -%}
                                         {{ submodel.reference.class_name }},
{%- endfor %}]
{% else %}
{{ make_model(model) }}
{% endif %}
