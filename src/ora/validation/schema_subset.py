"""Deterministic schema and YAML-subset validation for ORA Slice 2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_SCHEMA_KEYS = {
    "$schema",
    "$id",
    "title",
    "description",
    "type",
    "minimum",
    "additionalProperties",
    "required",
    "properties",
    "items",
    "enum",
}


@dataclass(frozen=True)
class ValidationResult:
    """Represents deterministic validation findings."""

    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


class YamlSubsetError(ValueError):
    """Raised when a YAML document falls outside the supported subset."""


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml_subset_file(path: Path) -> Any:
    return parse_yaml_subset(path.read_text(encoding="utf-8"), source_name=str(path))


def parse_yaml_subset(text: str, source_name: str = "<string>") -> Any:
    parser = _YamlSubsetParser(text=text, source_name=source_name)
    return parser.parse()


def validate_schema_support(schema: Any, schema_path: str = "$") -> list[str]:
    errors: list[str] = []
    _validate_schema_support(schema, schema_path, errors)
    return errors


def validate_instance(instance: Any, schema: Any, instance_path: str = "$") -> list[str]:
    errors = validate_schema_support(schema)
    if errors:
        return errors

    result: list[str] = []
    _validate_instance(instance, schema, instance_path, result)
    return result


def build_collection_schema(collection_key: str, item_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [collection_key],
        "properties": {
            collection_key: {
                "type": "array",
                "items": item_schema,
            }
        },
    }


def _validate_schema_support(schema: Any, schema_path: str, errors: list[str]) -> None:
    if not isinstance(schema, dict):
        errors.append(f"{schema_path}: schema must be an object")
        return

    unsupported = sorted(key for key in schema if key not in SUPPORTED_SCHEMA_KEYS)
    if unsupported:
        errors.append(
            f"{schema_path}: unsupported schema keywords: {', '.join(unsupported)}"
        )

    if "type" in schema:
        type_value = schema["type"]
        if isinstance(type_value, str):
            allowed_types = [type_value]
        elif isinstance(type_value, list) and type_value:
            allowed_types = type_value
        else:
            errors.append(f"{schema_path}.type: expected string or non-empty list")
            allowed_types = []

        valid_types = {"object", "array", "string", "boolean", "null", "integer", "number"}
        invalid_types = [entry for entry in allowed_types if entry not in valid_types]
        if invalid_types:
            errors.append(
                f"{schema_path}.type: unsupported type values: {', '.join(invalid_types)}"
            )

    if "required" in schema and not (
        isinstance(schema["required"], list)
        and all(isinstance(entry, str) for entry in schema["required"])
    ):
        errors.append(f"{schema_path}.required: expected list of strings")

    if "enum" in schema and not isinstance(schema["enum"], list):
        errors.append(f"{schema_path}.enum: expected list")

    if "minimum" in schema and not isinstance(schema["minimum"], (int, float)):
        errors.append(f"{schema_path}.minimum: expected number")

    if "properties" in schema:
        properties = schema["properties"]
        if not isinstance(properties, dict):
            errors.append(f"{schema_path}.properties: expected object")
        else:
            for name, property_schema in properties.items():
                _validate_schema_support(
                    property_schema,
                    f"{schema_path}.properties.{name}",
                    errors,
                )

    if "items" in schema:
        _validate_schema_support(schema["items"], f"{schema_path}.items", errors)


def _validate_instance(
    instance: Any,
    schema: dict[str, Any],
    instance_path: str,
    errors: list[str],
) -> None:
    if "type" in schema and not _matches_type(instance, schema["type"]):
        expected = schema["type"]
        if isinstance(expected, list):
            expected_display = " or ".join(expected)
        else:
            expected_display = expected
        errors.append(f"{instance_path}: expected {expected_display}")
        return

    if "enum" in schema and instance not in schema["enum"]:
        allowed = ", ".join(repr(entry) for entry in schema["enum"])
        errors.append(f"{instance_path}: expected one of {allowed}")
        return

    if "minimum" in schema and isinstance(instance, (int, float)):
        if instance < schema["minimum"]:
            errors.append(f"{instance_path}: expected >= {schema['minimum']}")
            return

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        if "object" in schema_type and isinstance(instance, dict):
            schema_type = "object"
        elif "array" in schema_type and isinstance(instance, list):
            schema_type = "array"
        elif "string" in schema_type and isinstance(instance, str):
            schema_type = "string"
        elif "boolean" in schema_type and isinstance(instance, bool):
            schema_type = "boolean"
        elif "integer" in schema_type and isinstance(instance, int) and not isinstance(instance, bool):
            schema_type = "integer"
        elif "number" in schema_type and isinstance(instance, (int, float)) and not isinstance(instance, bool):
            schema_type = "number"
        elif instance is None and "null" in schema_type:
            schema_type = "null"
        else:
            return

    if schema_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{instance_path}: missing required key '{key}'")

        if schema.get("additionalProperties") is False:
            extra_keys = sorted(key for key in instance if key not in properties)
            for key in extra_keys:
                errors.append(f"{instance_path}: unexpected key '{key}'")

        for key, property_schema in properties.items():
            if key in instance:
                _validate_instance(
                    instance[key],
                    property_schema,
                    f"{instance_path}.{key}",
                    errors,
                )

    elif schema_type == "array":
        item_schema = schema.get("items")
        if item_schema is None:
            return
        for index, entry in enumerate(instance):
            _validate_instance(entry, item_schema, f"{instance_path}[{index}]", errors)


def _matches_type(instance: Any, expected_type: str | list[str]) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(instance, entry) for entry in expected_type)
    if expected_type == "object":
        return isinstance(instance, dict)
    if expected_type == "array":
        return isinstance(instance, list)
    if expected_type == "string":
        return isinstance(instance, str)
    if expected_type == "boolean":
        return isinstance(instance, bool)
    if expected_type == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected_type == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected_type == "null":
        return instance is None
    return False


class _YamlSubsetParser:
    def __init__(self, text: str, source_name: str) -> None:
        self.lines = text.splitlines()
        self.source_name = source_name

    def parse(self) -> Any:
        start = self._next_content_index(0)
        if start >= len(self.lines):
            return {}
        value, index = self._parse_block(start, 0)
        remainder = self._next_content_index(index)
        if remainder < len(self.lines):
            raise YamlSubsetError(
                f"{self.source_name}:{remainder + 1}: unexpected trailing content"
            )
        return value

    def _parse_block(self, index: int, indent: int) -> tuple[Any, int]:
        index = self._next_content_index(index)
        if index >= len(self.lines):
            raise YamlSubsetError(f"{self.source_name}: expected content at indent {indent}")

        current_indent = self._line_indent(index)
        if current_indent != indent:
            raise YamlSubsetError(
                f"{self.source_name}:{index + 1}: expected indent {indent}, found {current_indent}"
            )

        content = self.lines[index][indent:]
        if content.startswith("- "):
            return self._parse_sequence(index, indent)
        return self._parse_mapping(index, indent)

    def _parse_mapping(self, index: int, indent: int) -> tuple[dict[str, Any], int]:
        mapping: dict[str, Any] = {}
        while index < len(self.lines):
            index = self._next_content_index(index)
            if index >= len(self.lines):
                break
            current_indent = self._line_indent(index)
            if current_indent < indent:
                break
            if current_indent != indent:
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: unexpected indent {current_indent}"
                )

            content = self.lines[index][indent:]
            if content.startswith("- "):
                break
            key, has_inline_value, inline_value = self._split_mapping_entry(content, index)
            if key in mapping:
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: duplicate key '{key}'"
                )

            if has_inline_value:
                mapping[key] = self._parse_scalar(inline_value)
                index += 1
                continue

            child_index = self._next_content_index(index + 1)
            if child_index >= len(self.lines):
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: missing nested value for '{key}'"
                )
            child_indent = self._line_indent(child_index)
            if child_indent <= indent:
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: missing nested value for '{key}'"
                )

            mapping[key], index = self._parse_block(child_index, indent + 2)
        return mapping, index

    def _parse_sequence(self, index: int, indent: int) -> tuple[list[Any], int]:
        items: list[Any] = []
        while index < len(self.lines):
            index = self._next_content_index(index)
            if index >= len(self.lines):
                break
            current_indent = self._line_indent(index)
            if current_indent < indent:
                break
            if current_indent != indent:
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: unexpected indent {current_indent}"
                )

            content = self.lines[index][indent:]
            if not content.startswith("- "):
                break

            item_content = content[2:]
            if not item_content:
                child_index = self._next_content_index(index + 1)
                if child_index >= len(self.lines):
                    raise YamlSubsetError(
                        f"{self.source_name}:{index + 1}: missing nested sequence item"
                    )
                item, index = self._parse_block(child_index, indent + 2)
                items.append(item)
                continue

            if ":" in item_content:
                item, index = self._parse_sequence_mapping_item(item_content, index, indent)
                items.append(item)
                continue

            items.append(self._parse_scalar(item_content))
            index += 1
        return items, index

    def _parse_sequence_mapping_item(
        self,
        content: str,
        index: int,
        indent: int,
    ) -> tuple[dict[str, Any], int]:
        key, has_inline_value, inline_value = self._split_mapping_entry(content, index)
        mapping: dict[str, Any] = {}
        if has_inline_value:
            mapping[key] = self._parse_scalar(inline_value)
        else:
            child_index = self._next_content_index(index + 1)
            if child_index >= len(self.lines):
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: missing nested value for '{key}'"
                )
            mapping[key], index = self._parse_block(child_index, indent + 2)
            return mapping, index

        index += 1
        while index < len(self.lines):
            index = self._next_content_index(index)
            if index >= len(self.lines):
                break
            current_indent = self._line_indent(index)
            if current_indent <= indent:
                break
            if current_indent != indent + 2:
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: unexpected indent {current_indent}"
                )

            entry = self.lines[index][indent + 2 :]
            if entry.startswith("- "):
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: nested sequences in mapping items are unsupported"
                )

            nested_key, has_inline_nested, nested_inline = self._split_mapping_entry(entry, index)
            if nested_key in mapping:
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: duplicate key '{nested_key}'"
                )

            if has_inline_nested:
                mapping[nested_key] = self._parse_scalar(nested_inline)
                index += 1
                continue

            child_index = self._next_content_index(index + 1)
            if child_index >= len(self.lines):
                raise YamlSubsetError(
                    f"{self.source_name}:{index + 1}: missing nested value for '{nested_key}'"
                )
            mapping[nested_key], index = self._parse_block(child_index, indent + 4)
        return mapping, index

    def _split_mapping_entry(self, content: str, index: int) -> tuple[str, bool, str]:
        if ":" not in content:
            raise YamlSubsetError(
                f"{self.source_name}:{index + 1}: expected mapping entry"
            )
        key, remainder = content.split(":", 1)
        key = key.strip()
        if not key:
            raise YamlSubsetError(f"{self.source_name}:{index + 1}: empty key is not allowed")
        if not remainder:
            return key, False, ""
        if not remainder.startswith(" "):
            raise YamlSubsetError(
                f"{self.source_name}:{index + 1}: expected a space after ':'"
            )
        return key, True, remainder[1:]

    def _parse_scalar(self, value: str) -> Any:
        if value == "[]":
            return []
        if value == "{}":
            return {}
        if value == "null":
            return None
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            return value[1:-1]
        if value.startswith("'") and value.endswith("'") and len(value) >= 2:
            return value[1:-1]
        return value

    def _line_indent(self, index: int) -> int:
        line = self.lines[index]
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            raise YamlSubsetError(
                f"{self.source_name}:{index + 1}: indentation must use 2-space increments"
            )
        return indent

    def _next_content_index(self, index: int) -> int:
        while index < len(self.lines):
            stripped = self.lines[index].strip()
            if stripped and not stripped.startswith("#"):
                break
            index += 1
        return index
