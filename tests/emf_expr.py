"""Minimal EMF/CEM expression compiler for tests.

Parses the expression language used in .jem/.jpm animations and compiles it
to Python. Names are read from a state mapping `S`; unknown names surface as
KeyError so typos in input variables fail loudly.
"""

import math
import re

_TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|([A-Za-z_][A-Za-z0-9_.:]*)|(&&|\|\||==|!=|<=|>=|[-+*/%<>!(),]))")

CONSTANTS = {"true": "True", "false": "False", "pi": repr(math.pi), "e": repr(math.e)}


def _frac(x):
    return x - math.floor(x)


def _random(seed=0.0):
    return _frac(math.sin(seed * 12.9898 + 78.233) * 43758.5453)


def _div(a, b):
    if b == 0:
        return math.copysign(math.inf, a) if a else math.nan
    return a / b


def _wrap(x, half):
    return (x + half) % (2 * half) - half


FUNCTIONS = {
    "clamp": lambda x, lo, hi: min(max(x, lo), hi),
    "lerp": lambda k, x, y: x + k * (y - x),
    "exp": math.exp, "sqrt": math.sqrt, "log": math.log, "abs": abs,
    "pow": lambda x, y: math.copysign(abs(x) ** y, x) if y % 2 == 1 else abs(x) ** y,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
    "torad": math.radians, "todeg": math.degrees,
    "min": min, "max": max, "floor": math.floor, "ceil": math.ceil, "round": round,
    "fmod": lambda x, y: x % y, "frac": _frac, "signum": lambda x: (x > 0) - (x < 0),
    "between": lambda x, lo, hi: lo <= x <= hi,
    "equals": lambda x, y, eps: abs(x - y) <= eps,
    "random": _random,
    "print": lambda _id, _n, x: x, "printb": lambda _id, _n, x: x,
    "wrapdeg": lambda x: _wrap(x, 180.0), "wraprad": lambda x: _wrap(x, math.pi),
}


def tokenize(text):
    pos, out = 0, []
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise SyntaxError(f"bad token at {pos}: {text[pos:pos + 20]!r}")
        pos = m.end()
        number, name, op = m.groups()
        out.append(("num", number) if number else ("id", name) if name else ("op", op))
    return out


class _Parser:
    BINARY = [("||",), ("&&",), ("==", "!="), ("<", "<=", ">", ">="), ("+", "-"), ("*", "/", "%")]

    def __init__(self, tokens):
        self.tokens, self.i = tokens, 0
        self.names, self.functions = set(), set()

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def take(self, value=None):
        tok = self.peek()
        if value is not None and tok[1] != value:
            raise SyntaxError(f"expected {value!r}, got {tok[1]!r}")
        self.i += 1
        return tok

    def parse(self):
        code = self.binary(0)
        if self.i != len(self.tokens):
            raise SyntaxError(f"trailing tokens: {self.tokens[self.i:]}")
        return code

    def binary(self, level):
        if level == len(self.BINARY):
            return self.unary()
        left = self.binary(level + 1)
        while self.peek()[0] == "op" and self.peek()[1] in self.BINARY[level]:
            op = self.take()[1]
            right = self.binary(level + 1)
            if op == "||":
                left = f"(bool({left}) or bool({right}))"
            elif op == "&&":
                left = f"(bool({left}) and bool({right}))"
            elif op == "/":
                left = f"_div({left}, {right})"
            elif op == "%":
                left = f"({left} % {right})"
            else:
                left = f"({left} {op} {right})"
        return left

    def unary(self):
        tok = self.peek()
        if tok == ("op", "!"):
            self.take()
            return f"(not {self.unary()})"
        if tok == ("op", "-"):
            self.take()
            return f"(-{self.unary()})"
        return self.primary()

    def primary(self):
        kind, value = self.take()
        if kind == "num":
            return value
        if kind == "op" and value == "(":
            inner = self.binary(0)
            self.take(")")
            return f"({inner})"
        if kind == "id":
            if self.peek() == ("op", "("):
                self.take()
                args = []
                if self.peek() != ("op", ")"):
                    args.append(self.binary(0))
                    while self.peek() == ("op", ","):
                        self.take()
                        args.append(self.binary(0))
                self.take(")")
                return self.call(value, args)
            if value in CONSTANTS:
                return CONSTANTS[value]
            self.names.add(value)
            return f"S[{value!r}]"
        raise SyntaxError(f"unexpected {value!r}")

    def call(self, name, args):
        self.functions.add(name)
        if name == "if":
            if len(args) < 3 or len(args) % 2 == 0:
                raise SyntaxError("if() needs cond,value pairs and an else value")
            code = args[-1]
            for i in range(len(args) - 3, -1, -2):
                code = f"({args[i + 1]} if {args[i]} else {code})"
            return code
        if name not in FUNCTIONS:
            raise SyntaxError(f"unknown function {name}()")
        return f"F[{name!r}]({', '.join(args)})"


# EMF's nbt(tag,query) takes raw text arguments; tests read it as an input "nbt__<tag>"
_NBT = re.compile(r"nbt\((\w+),[^)]*\)")


class Compiled:
    def __init__(self, text):
        parser = _Parser(tokenize(_NBT.sub(r"nbt__\1", text)))
        self.source = parser.parse()
        self.names = parser.names
        self.functions = parser.functions
        self.code = compile(self.source, "<emf>", "eval")

    def __call__(self, scope):
        """scope: dict from make_scope()."""
        return eval(self.code, scope)


def make_scope(state):
    return {"F": FUNCTIONS, "_div": _div, "S": state}
