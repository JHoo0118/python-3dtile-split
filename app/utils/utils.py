import argparse
from ifcopenshell.entity_instance import entity_instance
from pygltflib import Attributes

def extract_non_null_attributes(attributes: Attributes) -> dict:
    attributes_dict = (
        vars(attributes) if not isinstance(attributes, dict) else attributes
    )
    return {k: v for k, v in attributes_dict.items() if v is not None}

def to_dict(obj, exclude_keys: list[str]):
    if isinstance(obj, dict):
        return {k[0].lower() + k[1:]: to_dict(v, exclude_keys) for k, v in obj.items() if k not in exclude_keys}
    elif isinstance(obj, entity_instance):
        return {k[0].lower() + k[1:]: to_dict(v, exclude_keys) for k, v in vars(obj).items() if k not in exclude_keys}
    else:
        return obj