"""Shorthand for writing EMF expressions.

  $name  -> var.le_name      (float state, persists between frames)
  ?name  -> varb.le_name     (boolean state)
  #name  -> var.le_k_name    (tunable, see config.TUNABLES)
  @name  -> le_name          (part id)

A block is a list of (target, expression) pairs. EMF evaluates blocks in
order and the pairs inside a block in order, so later pairs see earlier ones.
"""

import re

from .config import PREFIX

_TOKENS = [
    (re.compile(r"\$(\w+)"), rf"var.{PREFIX}\1"),
    (re.compile(r"\?(\w+)"), rf"varb.{PREFIX}\1"),
    (re.compile(r"#(\w+)"), rf"var.{PREFIX}k_\1"),
    (re.compile(r"@(\w+)"), rf"{PREFIX}\1"),
]


def expand(text):
    for pattern, replacement in _TOKENS:
        text = pattern.sub(replacement, text)
    return text


def to_json_blocks(blocks):
    out = []
    for block in blocks:
        obj = {}
        for target, expression in block:
            key = expand(target)
            if key in obj:
                raise ValueError(f"duplicate target {key} in one block; split the block")
            obj[key] = expand(expression)
        out.append(obj)
    return out


def num(value):
    """Compact number literal for expressions and JSON."""
    value = round(float(value), 4)
    return int(value) if value == int(value) else value
