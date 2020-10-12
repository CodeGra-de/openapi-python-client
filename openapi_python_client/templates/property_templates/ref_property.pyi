{% macro _construct(property, source) %}
{% set model = property.reference.lookup() %}
{% if model.is_union %}
from . import {{ model.joins[0].reference.module_name }}

err = None
for opt in [{% for submodel in model.joins %}{{ submodel.reference.module_name }}.{{ submodel.reference.class_name }}, {% endfor %}]:
    try:
        {{ property.python_name }} = opt.from_dict(cast(Dict[str, Any], {{ source }}))
    except Exception as exc:
        err = exc
    else:
        break
else:
    raise err
del err
{% else %}
{{ property.python_name }} = {{ property.reference.class_name }}.from_dict(cast(Dict[str, Any], {{ source }}))
{% endif %}
{% endmacro %}

{% macro construct(property, source) %}
{% if property.required %}
{{ _construct(property, source) }}
{% else %}
{{ property.python_name }} = None
if {{ source }} is not None:
    {{ _construct(property, source) | indent(4) }}
{% endif %}
{% endmacro %}

{% macro transform(property, source, destination) %}
{% if property.required %}
{{ destination }} = maybe_to_dict({{ source }})
{% else %}
{{ destination }} = maybe_to_dict({{ source }}) if {{ source }} else None
{% endif %}
{% endmacro %}
