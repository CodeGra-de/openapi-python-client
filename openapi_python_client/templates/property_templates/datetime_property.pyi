{% macro construct(property, source) %}
{% if property.required and not property.nullable %}
{{ property.python_name }} = datetime.datetime.fromisoformat({{ source }})
{% else %}
{{ property.python_name }} = None
if {{ source }} is not None:
    {{ property.python_name }} = datetime.datetime.fromisoformat(cast(str, {{ source }}))
{% endif %}
{% endmacro %}

{% macro transform(property, source, destination) %}
{% if property.required and not property.nullable %}
{{ destination }} = {{ source }}.isoformat()
{% else %}
{{ destination }} = {{ source }}.isoformat() if {{ source }} else None
{% endif %}
{% endmacro %}
