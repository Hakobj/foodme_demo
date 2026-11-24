"""Maps changed Spring Boot sources to the REST endpoints they can affect.

- Controllers: `@RequestMapping` on the class + `@Get/Post/Put/Patch/DeleteMapping` on methods. String
  constants (`ControllerUtil.API_ORDER_CONTROLLER`) are resolved. A change inside one handler method
  selects only that endpoint; a change elsewhere in a controller selects all of its endpoints.
- Any other class (service, repository, model, dto, utils): every controller that reaches it through
  class-name references (transitively) is affected, with all of its endpoints.

Endpoints are normalised like the recorded ones: `GET /api/dish/{*}/active`.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

MAPPING_RE = re.compile(r"@(Get|Post|Put|Patch|Delete|Request)Mapping\s*(?:\((?P<args>[^)]*)\))?")
CONST_RE = re.compile(r"static\s+final\s+String\s+(\w+)\s*=\s*([^;]+);")
CLASS_RE = re.compile(r"\b(?:class|interface|enum|record)\s+(\w+)")
WORD_RE = re.compile(r"\b[A-Z]\w+\b")
PATH_VAR_RE = re.compile(r"\{[^}/]+\}")


def normalize_path(path: str) -> str:
    """`/api/dish/{chefId}/active` and `/api/dish/10/active` both become `/api/dish/{*}/active`."""
    path = path.split("?", 1)[0].rstrip("/") or "/"
    segments = []
    for segment in path.split("/"):
        if PATH_VAR_RE.fullmatch(segment) or segment.isdigit() or re.fullmatch(r"FM-\d+", segment):
            segments.append("{*}")
        else:
            segments.append(segment)
    return "/".join(segments)


def endpoint(method: str, path: str) -> str:
    return f"{method.upper()} {normalize_path(path)}"


@dataclass
class Handler:
    endpoint: str
    first_line: int  # the mapping annotation
    last_line: int  # the line before the next handler / end of class


@dataclass
class JavaFile:
    path: str  # repo-relative
    text: str
    classes: list[str] = field(default_factory=list)


class BackendIndex:
    def __init__(self, repo_root: Path, src_root: str = "apps/backend/src/main/java/"):
        self.repo_root = repo_root
        self.src_root = src_root
        self.files: dict[str, JavaFile] = {}
        base = repo_root / src_root
        for file in sorted(base.rglob("*.java")) if base.exists() else []:
            rel = file.relative_to(repo_root).as_posix()
            text = file.read_text(encoding="utf-8", errors="replace")
            self.files[rel] = JavaFile(rel, text, CLASS_RE.findall(text))

    # ---- string constants and controllers -------------------------------------------------

    @cached_property
    def constants(self) -> dict[str, str]:
        raw: dict[str, str] = {}
        for java in self.files.values():
            owner = java.classes[0] if java.classes else ""
            for name, expr in CONST_RE.findall(java.text):
                raw[name] = expr.strip()
                raw[f"{owner}.{name}"] = expr.strip()
        resolved: dict[str, str] = {}

        def resolve(name: str, depth: int = 0) -> str:
            if name in resolved:
                return resolved[name]
            if depth > 10 or name not in raw:
                return ""
            value = "".join(self._eval(part.strip(), resolve, depth) for part in raw[name].split("+"))
            resolved[name] = value
            return value

        for name in raw:
            resolve(name)
        return resolved

    @staticmethod
    def _eval(part: str, resolve, depth: int) -> str:
        if part.startswith('"') and part.endswith('"'):
            return part[1:-1]
        return resolve(part, depth + 1)

    def _mapping_paths(self, args: str | None) -> list[str]:
        if not args:
            return [""]
        # value = "/x" / path = {"/a", "/b"} / a bare constant or string concatenation
        match = re.search(r"(?:value|path)\s*=\s*(\{[^}]*\}|[^,]+)", args)
        expr = match.group(1) if match else args.split(",")[0]
        if "method" in expr and "=" in expr:
            return [""]
        options = [o for o in expr.strip("{} ").split(",") if o.strip()] or [""]
        paths = []
        for option in options:
            value = ""
            for raw in option.split("+"):
                part = raw.strip()
                value += part[1:-1] if part.startswith('"') else self.constants.get(part, "")
            paths.append(value)
        return paths

    def handlers(self, rel_path: str) -> list[Handler]:
        """Endpoints of a controller file with the line range of each handler method."""
        java = self.files.get(rel_path)
        if java is None or "@RestController" not in java.text and "@Controller" not in java.text:
            return []
        lines = java.text.splitlines()
        class_line = next((i for i, line in enumerate(lines) if CLASS_RE.search(line)), 0)
        prefixes = [""]
        found: list[tuple[int, str, list[str]]] = []
        for index, line in enumerate(lines):
            for match in MAPPING_RE.finditer(line):
                kind, args = match.group(1), match.group("args")
                paths = self._mapping_paths(args)
                if index < class_line:  # class-level @RequestMapping
                    prefixes = paths
                    continue
                method = {"Request": "ANY"}.get(kind, kind.upper())
                if kind == "Request" and args:
                    verb = re.search(r"RequestMethod\.(\w+)", args)
                    method = verb.group(1) if verb else "ANY"
                found.append((index + 1, method, paths))
        result = []
        for n, (line_no, method, paths) in enumerate(found):
            last = found[n + 1][0] - 1 if n + 1 < len(found) else len(lines)
            for prefix in prefixes:
                for path in paths:
                    result.append(Handler(endpoint(method, prefix + path), line_no, last))
        return result

    @cached_property
    def controllers(self) -> dict[str, list[Handler]]:
        return {rel: hs for rel in self.files if (hs := self.handlers(rel))}

    # ---- reference graph ---------------------------------------------------------------------

    @cached_property
    def _class_to_file(self) -> dict[str, str]:
        return {cls: java.path for java in self.files.values() for cls in java.classes}

    @cached_property
    def _referenced_by(self) -> dict[str, set[str]]:
        """file -> files that mention one of its classes."""
        graph: dict[str, set[str]] = {rel: set() for rel in self.files}
        for java in self.files.values():
            for word in set(WORD_RE.findall(java.text)):
                target = self._class_to_file.get(word)
                if target and target != java.path:
                    graph[target].add(java.path)
        return graph

    def controllers_reaching(self, rel_path: str) -> set[str]:
        seen, queue = {rel_path}, deque([rel_path])
        while queue:
            for user in self._referenced_by.get(queue.popleft(), ()):
                if user not in seen:
                    seen.add(user)
                    queue.append(user)
        return {f for f in seen if f in self.controllers}

    def endpoints_for_change(self, rel_path: str, changed_lines: set[int] | None = None) -> set[str]:
        """Endpoints a change to `rel_path` can affect. `changed_lines` (new-file line numbers) narrows a
        controller change to the handler methods it touches."""
        own = self.controllers.get(rel_path)
        if own and changed_lines:
            first_handler = min(h.first_line for h in own)
            touched = {
                h.endpoint
                for h in own
                for line in changed_lines
                if line >= first_handler and h.first_line - 3 <= line <= h.last_line
            }
            outside = any(line < first_handler - 3 for line in changed_lines)
            if touched and not outside:
                return touched
        result: set[str] = set()
        for controller in self.controllers_reaching(rel_path):
            result.update(h.endpoint for h in self.controllers[controller])
        return result
