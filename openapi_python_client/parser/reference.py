""" A Reference is ultimately a Class which will be in models, usually defined in a body input or return type """

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

from .. import utils

if TYPE_CHECKING:
    from .openapi import Model

class_overrides: Dict[str, Reference] = {}



@dataclass(frozen=True)
class Reference:
    """ A reference to a class which will be in models """

    class_name: str
    module_name: str

    def lookup(self) -> 'Model':
        from .openapi import ALL_MODELS
        return ALL_MODELS[self]

    @staticmethod
    def from_ref(ref: str) -> Reference:
        """ Get a Reference from the openapi #/schemas/blahblah string """
        ref_value = ref.split("/")[-1]
        # ugly hack to avoid stringcase ugly pascalcase output when ref_value isn't snake case
        class_name = utils.pascal_case(ref_value.replace(" ", ""))

        if class_name in class_overrides:
            return class_overrides[class_name]

        return Reference(class_name=class_name, module_name=utils.snake_case(class_name))
