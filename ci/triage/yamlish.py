"""A tiny YAML writer for the run files (no PyYAML dependency). Strings are emitted as JSON strings,
which are valid YAML double-quoted scalars, so the output always parses."""

from __future__ import annotations

import json
from typing import Any


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    return json.dumps(str(value), ensure_ascii=False)


def dump_yaml(data: Any, indent: int = 0) -> str:
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)) and value:
                lines.append(f"{pad}{key}:")
                lines.append(dump_yaml(value, indent + 1).rstrip("\n"))
            elif isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}: {'{}' if isinstance(value, dict) else '[]'}")
            else:
                lines.append(f"{pad}{key}: {_scalar(value)}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item:
                first, *rest = dump_yaml(item, indent + 1).rstrip("\n").split("\n")
                lines.append(f"{pad}- {first.strip()}")
                lines.extend(rest)
            else:
                lines.append(f"{pad}- {_scalar(item)}")
    else:
        lines.append(f"{pad}{_scalar(data)}")
    return "\n".join(lines) + "\n"
