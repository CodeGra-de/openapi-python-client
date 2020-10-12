{% macro construct(property, source) %}
if {{ source }} != {{ property.repr_value }}:
    raise ValueError('{{ "Wrong value for " + property.python_name + ": "}}' + {{ source }})
{{ property.python_name }} = {{ source }}
{% endmacro %}

{% macro transform(property, source, destination) %}
{{ destination }} = {{ source }}
{% endmacro %}
