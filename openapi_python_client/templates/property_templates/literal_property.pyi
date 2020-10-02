{% macro construct(property, source) %}
{{ property.python_name }} = {{ source }}
{% endmacro %}

{% macro transform(property, source, destination) %}
{{ destination }} = {{ source }}
{% endmacro %}
