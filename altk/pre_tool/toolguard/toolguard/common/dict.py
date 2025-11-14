from typing import Dict, Any, Callable
import hashlib
import json
from collections import deque


def dict_deep_merge(trg_dct: Dict, merge_dct: Dict):
    for k, v in merge_dct.items():
        trg_v = trg_dct.get(k)
        if k in trg_dct and isinstance(trg_v, dict) and isinstance(v, dict):
            dict_deep_merge(trg_v, v)
        elif isinstance(trg_v, list) and isinstance(v, list):
            if all([type(item) is dict for item in v]) and all(
                [type(item) is dict for item in trg_v]
            ):  # both are lists of objects
                for a, b in zip(trg_v, v):
                    dict_deep_merge(a, b)
            else:
                for item in v:
                    if item not in trg_dct[k]:
                        trg_dct[k].append(item)
        else:
            trg_dct[k] = v


def get_keys_recursive(d: Dict):
    keys = []
    for key, value in d.items():
        keys.append(key)
        if isinstance(value, dict):
            keys.extend(get_keys_recursive(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    keys.extend(get_keys_recursive(item))
    return keys


# adapted from https://www.doc.ic.ac.uk/~nuric/posts/coding/how-to-hash-a-dictionary-in-python/
def dict_hash(dictionary: Dict[str, Any]) -> int:
    encoded = json.dumps(dictionary, sort_keys=True).encode()
    return int(hashlib.sha256(encoded).hexdigest(), 16)


def visit_all(d: Any, cb: Callable[[Dict, Any], bool]):
    if type(d) is dict:
        for k in list(
            d
        ):  # list() to avoid RuntimeError: dictionary changed size during iteration
            changed = cb(d, k)
            if not changed:
                visit_all(d[k], cb)
    if type(d) is list:
        for item in d:
            visit_all(item, cb)


def resolve_ref(ref, root_schema, resolved_refs):
    """Resolve a $ref to its actual definition in the schema."""
    if ref in resolved_refs:
        return resolved_refs[ref]

    resolved_schema = find_ref(root_schema, ref)
    resolved_refs[ref] = resolved_schema
    return substitute_refs(resolved_schema, root_schema, resolved_refs)


def substitute_refs(schema, root_schema=None, resolved_refs=None):
    """Substitute all $refs in the JSON schema with their definitions."""
    if root_schema is None:
        root_schema = schema
    if resolved_refs is None:
        resolved_refs = {}

    if isinstance(schema, dict):
        if "$ref" in schema:
            ref = schema["$ref"]
            if ref in resolved_refs:
                return resolved_refs[ref]
            resolved = resolve_ref(ref, root_schema, resolved_refs)
            resolved_refs[ref] = resolved
            return resolved
        else:
            return {
                k: substitute_refs(v, root_schema, resolved_refs)
                for k, v in schema.items()
            }
    elif isinstance(schema, list):
        return [substitute_refs(item, root_schema, resolved_refs) for item in schema]
    else:
        return schema


def find_ref(doc: dict, ref: str):
    q = deque(ref.split("/"))
    cur = doc
    while q:
        field = q.popleft()
        if field == "#":
            cur = doc
            continue
        if field in cur:
            cur = cur[field]
        else:
            return None
    if "$ref" in cur:
        return find_ref(doc, cur.get("$ref"))  # recursive. infinte loops?
    return cur
