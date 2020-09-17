from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import ValidationError

from .. import schema as oai
from .. import utils
from .errors import GeneratorError, ParseError, PropertyError
from .properties import EnumProperty, Property, RefProperty, property_from_data
from .reference import Reference
from .responses import ListRefResponse, RefResponse, Response, UnionResponse, response_from_data


class ParameterLocation(str, Enum):
    """ The places Parameters can be put when calling an Endpoint """

    QUERY = "query"
    PATH = "path"
    HEADER = "header"


def import_string_from_reference(reference: Reference, prefix: str = "") -> str:
    """ Create a string which is used to import a reference """
    return f"from {prefix}.{reference.module_name} import {reference.class_name}"


@dataclass
class EndpointCollection:
    """ A bunch of endpoints grouped under a tag that will become a module """

    tag: str
    endpoints: List[Endpoint] = field(default_factory=list)
    relative_imports: Set[str] = field(default_factory=set)
    parse_errors: List[ParseError] = field(default_factory=list)

    @staticmethod
    def from_data(*, data: Dict[str, oai.PathItem], base_responses: Any) -> Dict[str, EndpointCollection]:
        """ Parse the openapi paths data to get EndpointCollections by tag """
        endpoints_by_tag: Dict[str, EndpointCollection] = {}

        methods = ["get", "put", "post", "delete", "options", "head", "patch", "trace"]

        for path, path_data in data.items():
            for method in methods:
                operation: Optional[oai.Operation] = getattr(path_data, method)
                if operation is None:
                    continue
                tag = (operation.tags or ["default"])[0]
                collection = endpoints_by_tag.setdefault(tag, EndpointCollection(tag=tag))
                endpoint = Endpoint.from_data(data=operation, path=path, method=method, tag=tag, base_responses=base_responses)
                if isinstance(endpoint, ParseError):
                    endpoint.header = (
                        f"ERROR parsing {method.upper()} {path} within {tag}. Endpoint will not be generated."
                    )
                    collection.parse_errors.append(endpoint)
                    continue

                collection.endpoints.append(endpoint)
                collection.relative_imports.update(endpoint.relative_imports)

        return endpoints_by_tag


@dataclass
class Endpoint:
    """
    Describes a single endpoint on the server
    """

    path: str
    method: str
    description: Optional[str]
    name: str
    requires_security: bool
    tag: str
    relative_imports: Set[str] = field(default_factory=set)
    query_parameters: List[Property] = field(default_factory=list)
    path_parameters: List[Property] = field(default_factory=list)
    header_parameters: List[Property] = field(default_factory=list)
    responses: List[Response] = field(default_factory=list)
    form_body_reference: Optional[Reference] = None
    json_body: Optional[Property] = None
    multipart_body_reference: Optional[Reference] = None

    @staticmethod
    def parse_request_form_body(body: oai.RequestBody) -> Optional[Reference]:
        """ Return form_body_reference """
        body_content = body.content
        form_body = body_content.get("application/x-www-form-urlencoded")
        if form_body is not None and isinstance(form_body.media_type_schema, oai.Reference):
            return Reference.from_ref(form_body.media_type_schema.ref)
        return None

    @staticmethod
    def parse_multipart_body(body: oai.RequestBody) -> Optional[Reference]:
        """ Return form_body_reference """
        body_content = body.content
        json_body = body_content.get("multipart/form-data")
        if json_body is not None and isinstance(json_body.media_type_schema, oai.Reference):
            return Reference.from_ref(json_body.media_type_schema.ref)
        return None

    @staticmethod
    def parse_request_json_body(body: oai.RequestBody) -> Union[Property, PropertyError, None]:
        """ Return json_body """
        body_content = body.content
        json_body = body_content.get("application/json")
        if json_body is not None and json_body.media_type_schema is not None:
            return property_from_data("json_body", required=True, data=json_body.media_type_schema)
        return None

    @staticmethod
    def _add_body(endpoint: Endpoint, data: oai.Operation) -> Union[ParseError, Endpoint]:
        """ Adds form or JSON body to Endpoint if included in data """
        endpoint = deepcopy(endpoint)
        if data.requestBody is None or isinstance(data.requestBody, oai.Reference):
            return endpoint

        endpoint.form_body_reference = Endpoint.parse_request_form_body(data.requestBody)
        json_body = Endpoint.parse_request_json_body(data.requestBody)
        if isinstance(json_body, ParseError):
            return ParseError(detail=f"cannot parse body of endpoint {endpoint.name}", data=json_body.data)

        endpoint.multipart_body_reference = Endpoint.parse_multipart_body(data.requestBody)

        if endpoint.form_body_reference:
            endpoint.relative_imports.add(import_string_from_reference(endpoint.form_body_reference, prefix="..models"))
        if endpoint.multipart_body_reference:
            endpoint.relative_imports.add(
                import_string_from_reference(endpoint.multipart_body_reference, prefix="..models")
            )
        if json_body is not None:
            endpoint.json_body = json_body
            endpoint.relative_imports.update(endpoint.json_body.get_imports(prefix="..models"))
        return endpoint

    @staticmethod
    def _add_responses(endpoint: Endpoint, data: oai.Responses, base_responses: Any) -> Union[Endpoint, ParseError]:
        endpoint = deepcopy(endpoint)

        def process_response(response: Response):
            if isinstance(response, (RefResponse, ListRefResponse)):
                endpoint.relative_imports.add(import_string_from_reference(response.reference, prefix="..models"))
            elif isinstance(response, UnionResponse):
                for opt in response.options:
                    process_response(opt)

        for code, response_data in data.items():
            try:
                code = int(code)
            except ValueError:
                assert (
                    (len(code) == 3 and code.endswith('XX')) or
                    code == 'default'
                )
                code = f'"{code}"'
            response = response_from_data(status_code=code, data=response_data, base_responses=base_responses)
            if isinstance(response, ParseError):
                return ParseError(detail=f"cannot parse response of endpoint {endpoint.name}", data=response.data)
            process_response(response)
            endpoint.responses.append(response)
        return endpoint

    @staticmethod
    def _add_parameters(endpoint: Endpoint, data: oai.Operation) -> Union[Endpoint, ParseError]:
        endpoint = deepcopy(endpoint)
        if data.parameters is None:
            return endpoint
        for param in data.parameters:
            if isinstance(param, oai.Reference) or param.param_schema is None:
                continue
            prop = property_from_data(name=param.name, required=param.required, data=param.param_schema)
            if isinstance(prop, ParseError):
                return ParseError(detail=f"cannot parse parameter of endpoint {endpoint.name}", data=prop.data)
            endpoint.relative_imports.update(prop.get_imports(prefix="..models"))

            if param.param_in == ParameterLocation.QUERY:
                endpoint.query_parameters.append(prop)
            elif param.param_in == ParameterLocation.PATH:
                endpoint.path_parameters.append(prop)
            elif param.param_in == ParameterLocation.HEADER:
                endpoint.header_parameters.append(prop)
            else:
                return ParseError(data=param, detail="Parameter must be declared in path or query")
        return endpoint

    @staticmethod
    def from_data(*, data: oai.Operation, path: str, method: str, tag: str, base_responses: Any) -> Union[Endpoint, ParseError]:
        """ Construct an endpoint from the OpenAPI data """

        if data.operationId is None:
            return ParseError(data=data, detail="Path operations with operationId are not yet supported")

        name = data.operationId.split('_', 1)[1]

        endpoint = Endpoint(
            path=path,
            method=method,
            description=utils.remove_string_escapes(data.description) if data.description else "",
            name=name,
            requires_security=bool(data.security),
            tag=tag,
        )

        result = Endpoint._add_parameters(endpoint, data)
        if isinstance(result, ParseError):
            return result
        result = Endpoint._add_responses(result, data.responses, base_responses=base_responses)
        if isinstance(result, ParseError):
            return result
        result = Endpoint._add_body(result, data)

        return result

ALL_MODELS: Dict[Reference, 'Model'] = {}

@dataclass
class Model:
    """
    A data model used by the API- usually a Schema with type "object".

    These will all be converted to dataclasses in the client
    """

    reference: Reference
    required_properties: List[Property]
    optional_properties: List[Property]
    description: str
    relative_imports: Set[str]
    inherits: Optional[Reference]
    is_error: bool
    is_union: bool = False

    @staticmethod
    def from_data(*, data: oai.Schema, name: str) -> Union[Model, ParseError]:
        """ A single Model from its OAI data

        Args:
            data: Data of a single Schema
            name: Name by which the schema is referenced, such as a model name.
                Used to infer the type name if a `title` property is not available.
        """
        required_set = set(data.required or [])
        required_properties: List[Property] = []
        optional_properties: List[Property] = []
        relative_imports: Set[str] = set()

        ref = Reference.from_ref(data.title or name)

        inherits = None
        props = data.properties
        if not props and data.allOf:
            assert len(data.allOf) == 2
            assert isinstance(data.allOf[0], oai.Reference)
            assert isinstance(data.allOf[1], oai.Schema)
            inherits = Reference.from_ref(ref=data.allOf[0].ref)
            relative_imports.add(f"from .{inherits.module_name} import {inherits.class_name}")
            props = data.allOf[1].properties
        elif not props:
            breakpoint()
            props = {}
            # raise AssertionError('Found empty property!')


        for key, value in props.items():
            required = key in required_set
            p = property_from_data(name=key, required=required, data=value)
            if isinstance(p, ParseError):
                return p
            if required:
                required_properties.append(p)
            else:
                optional_properties.append(p)

            relative_imports.update(p.get_imports(prefix=""))

        model = Model(
            reference=ref,
            required_properties=required_properties,
            optional_properties=optional_properties,
            relative_imports=relative_imports,
            description=data.description or "",
            inherits=inherits,
            is_error=getattr(data, 'x-is-error', False),
        )
        ALL_MODELS[ref] = model
        return model

@dataclass
class MyUnion:
    reference: Reference
    joins: List[Model]
    relative_imports: t.List[str]
    is_union: bool = True

    @staticmethod
    def from_data(*, data: oai.Schema, name: str) -> Union[MyUnion]:
        ref = Reference.from_ref(data.title or name)
        name = data.title or name

        return MyUnion(
            reference=ref,
            joins=[Model.from_data(data=opt, name=f'{name}_{idx + 1}') for idx, opt in enumerate(data.anyOf)],
            relative_imports=[]
        )

@dataclass
class Schemas:
    """ Contains all the Schemas (references) for an OpenAPI document """

    models: Dict[str, Model] = field(default_factory=dict)
    errors: List[ParseError] = field(default_factory=list)

    @staticmethod
    def build(*, schemas: Dict[str, Union[oai.Reference, oai.Schema]]) -> Schemas:
        """ Get a list of Schemas from an OpenAPI dict """
        result = Schemas()
        for name, data in schemas.items():
            if isinstance(data, oai.Reference):
                result.errors.append(ParseError(data=data, detail="Reference schemas are not supported."))
                continue
            if data.enum is not None:
                EnumProperty(
                    name=name,
                    title=data.title or name,
                    required=True,
                    default=data.default,
                    values=EnumProperty.values_from_list(data.enum),
                    nullable=data.nullable,
                )
                continue
            if data.anyOf:
                s = MyUnion.from_data(data=data, name=name)
            else:
                s = Model.from_data(data=data, name=name)
            if isinstance(s, ParseError):
                result.errors.append(s)
            else:
                result.models[s.reference.class_name] = s
        return result


@dataclass
class GeneratorData:
    """ All the data needed to generate a client """

    title: str
    description: Optional[str]
    version: str
    schemas: Schemas
    endpoint_collections_by_tag: Dict[str, EndpointCollection]
    enums: Dict[str, EnumProperty]

    @staticmethod
    def from_dict(d: Dict[str, Dict[str, Any]]) -> Union[GeneratorData, GeneratorError]:
        """ Create an OpenAPI from dict """
        try:
            openapi = oai.OpenAPI.parse_obj(d)
        except ValidationError as e:
            return GeneratorError(header="Failed to parse OpenAPI document", detail=str(e))
        if openapi.components is None or openapi.components.schemas is None:
            schemas = Schemas()
        else:
            schemas = Schemas.build(schemas=openapi.components.schemas)
        endpoint_collections_by_tag = EndpointCollection.from_data(data=openapi.paths, base_responses=openapi.components.responses)
        enums = EnumProperty.get_all_enums()

        return GeneratorData(
            title=openapi.info.title,
            description=openapi.info.description,
            version=openapi.info.version,
            endpoint_collections_by_tag=endpoint_collections_by_tag,
            schemas=schemas,
            enums=enums,
        )
