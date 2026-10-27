#!/usr/bin/env python3
"""A small, inspectable Jeetu-to-C compiler. Python 3.9+, C11."""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass


__version__ = "0.1"


class Error(Exception):
    pass


@dataclass
class Token:
    text: str
    line: int
    col: int


KEYWORDS = set('शुरू मान लो जब तक अगर वरना बोलो सच झूठ डालो निकालो आखिरी खाली कार्य लौटाओ पूर्णांक बूलियन रुको जारी पाठ सूची लंबाई लिखो'.split())
IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z_0-9]*')
PATTERN = re.compile(
    r'(?P<space>\s+)'
    r'|(?P<comment>//[^\n]*)'
    r'|(?P<string>"(?:[^"\\\n]|\\[^\n])*")'
    r'|(?P<num>[0-9]+)'
    r'|(?P<op>==|!=|<=|>=|&&|\|\||[{}()\[\];,:+*/%!=<>-])'
)


def lex(source):
    tokens = []
    pos, line, col = 0, 1, 1
    while pos < len(source):
        # Python's Unicode identifier rules include Devanagari vowel marks.
        if source[pos].isidentifier():
            end = pos + 1
            while end < len(source) and ('a' + source[end]).isidentifier():
                end += 1
            value, category = source[pos:end], 'id'
        else:
            m = PATTERN.match(source, pos)
            if not m:
                raise Error(f'{line}:{col}: unexpected character {source[pos]!r}')
            value, category, end = m.group(), m.lastgroup, m.end()
        if category not in ('space', 'comment'):
            if category == 'id' and value not in KEYWORDS and not IDENTIFIER.fullmatch(value):
                raise Error(f'{line}:{col}: variable names must use ASCII English letters, digits and underscore')
            tokens.append(Token(value, line, col))
        if '\n' in value:
            line += value.count('\n')
            col = len(value.rsplit('\n', 1)[1]) + 1
        else:
            col += len(value)
        pos = end
    tokens.append(Token('<eof>', line, col))
    return tokens


class Parser:
    precedence = {'||': 1, '&&': 2, '==': 3, '!=': 3, '<': 4, '<=': 4,
                  '>': 4, '>=': 4, '+': 5, '-': 5, '*': 6, '/': 6, '%': 6}

    def __init__(self, source):
        self.tokens = lex(source)
        self.i = 0

    def peek(self):
        return self.tokens[self.i].text

    def take(self, expected=None):
        token = self.tokens[self.i]
        if expected is not None and token.text != expected:
            self.fail(token, f'expected {expected!r}, found {token.text!r}')
        self.i += 1
        return token

    @staticmethod
    def fail(token, message):
        raise Error(f'{token.line}:{token.col}: {message}')

    def name(self):
        token = self.take()
        if not IDENTIFIER.fullmatch(token.text) or token.text in KEYWORDS:
            self.fail(token, 'expected a variable name')
        return token

    def type_name(self):
        token = self.take()
        types = {'पूर्णांक': 'int', 'बूलियन': 'bool', 'पाठ': 'text', 'सूची': 'seq'}
        if token.text not in types:
            self.fail(token, 'expected पूर्णांक, बूलियन, पाठ or सूची')
        return types[token.text]

    def parse(self):
        functions = []
        while self.peek() == 'कार्य':
            self.take()
            name = self.name()
            self.take('(')
            parameters = []
            if self.peek() != ')':
                while True:
                    parameter = self.name()
                    self.take(':')
                    parameters.append((parameter, self.type_name()))
                    if self.peek() != ',':
                        break
                    self.take(',')
            self.take(')')
            self.take(':')
            result = self.type_name()
            functions.append(Function(name, parameters, result, self.block()))
        self.take('शुरू')
        body = self.block()
        self.take('<eof>')
        return functions, body

    def block(self):
        self.take('{')
        body = []
        while self.peek() not in ('}', '<eof>'):
            body.append(self.statement())
        self.take('}')
        return body

    def statement(self):
        t = self.tokens[self.i]
        if self.peek() in ('रुको', 'जारी'):
            op = self.take().text
            self.take(';')
            return ('break' if op == 'रुको' else 'continue', t)
        if self.peek() == 'लौटाओ':
            self.take()
            value = self.expr()
            self.take(';')
            return ('return', t, value)
        if self.peek() == '{':
            return ('block', t, self.block())
        if self.peek() == 'मान':
            self.take('मान')
            self.take('लो')
            name = self.name()
            self.take('=')
            value = self.expr()
            self.take(';')
            return ('decl', name, value)
        if self.peek() in ('बोलो', 'लिखो'):
            operation = self.take().text
            value = self.expr()
            self.take(';')
            return ('print' if operation == 'बोलो' else 'write', t, value)
        if self.peek() in ('अगर', 'जब'):
            op = self.take().text
            if op == 'जब':
                self.take('तक')
            self.take('(')
            cond = self.expr()
            self.take(')')
            body = self.block()
            other = []
            if op == 'अगर' and self.peek() == 'वरना':
                self.take()
                other = self.block()
            return ('if' if op == 'अगर' else 'while', t, cond, body, other)
        if self.peek() == 'डालो':
            self.take()
            self.take('(')
            name = self.name()
            self.take(',')
            value = self.expr()
            self.take(')')
            self.take(';')
            return ('push', name, value)
        name = self.name()
        self.take('=')
        value = self.expr()
        self.take(';')
        return ('assign', name, value)

    def expr(self, minimum=1):
        t = self.take()
        if t.text in ('-', '!'):
            left = ('unary', t, self.expr(7))
        elif t.text == '(':
            left = self.expr()
            self.take(')')
        elif t.text == '[':
            elements = []
            if self.peek() != ']':
                while True:
                    elements.append(self.expr())
                    if self.peek() != ',':
                        break
                    self.take(',')
            self.take(']')
            left = ('seq', t, elements)
        elif t.text == 'लंबाई':
            self.take('(')
            value = self.expr()
            self.take(')')
            left = ('length', t, value)
        elif t.text in ('सच', 'झूठ'):
            left = ('bool', t)
        elif t.text in ('निकालो', 'आखिरी', 'खाली'):
            self.take('(')
            name = self.name()
            self.take(')')
            left = ('call', t, name)
        elif t.text.startswith('"'):
            try:
                value = json.loads(t.text)
                value.encode('utf-8')
            except (ValueError, UnicodeError):
                self.fail(t, 'invalid string; use JSON string escapes')
            left = ('str', t, value)
        elif re.fullmatch('[0-9]+', t.text):
            left = ('int', t)
        elif IDENTIFIER.fullmatch(t.text) and t.text not in KEYWORDS:
            if self.peek() == '(':
                self.take()
                arguments = []
                if self.peek() != ')':
                    while True:
                        arguments.append(self.expr())
                        if self.peek() != ',':
                            break
                        self.take(',')
                self.take(')')
                left = ('invoke', t, arguments)
            else:
                left = ('var', t)
        else:
            self.fail(t, 'expected an expression')
        while self.peek() == '[':
            bracket = self.take()
            index = self.expr()
            self.take(']')
            left = ('index', bracket, left, index)
        while self.precedence.get(self.peek(), 0) >= minimum:
            op = self.take()
            right = self.expr(self.precedence[op.text] + 1)
            left = ('binary', op, left, right)
        return left


@dataclass
class Function:
    token: Token
    parameters: list
    result: str
    body: list
    c_name: str = ''


def returns(body):
    """Conservative all-path return check; loops alone never prove a return."""
    for node in body:
        if node[0] == 'return':
            return True
        if node[0] == 'block' and returns(node[2]):
            return True
        if node[0] == 'if' and returns(node[3]) and returns(node[4]):
            return True
    return False


@dataclass
class Binding:
    kind: str
    name: str
    read: bool = False
    borrowed: bool = False
    suppressed: bool = False

    def reference(self):
        return self.name if self.borrowed else "&" + self.name


@dataclass
class Expression:
    kind: str
    code: object
    # Includes reads of mutable stacks and operations that can fail.
    effect: bool = False


C_RESERVED = set('''
auto break case char const continue default do double else enum extern float for
goto if inline int long register restrict return short signed sizeof static struct
switch typedef union unsigned void volatile while alignas alignof bool true false
complex imaginary noreturn static_assert thread_local main
int8_t int16_t int32_t int64_t uint8_t uint16_t uint32_t uint64_t intptr_t uintptr_t
intmax_t uintmax_t size_t ptrdiff_t wchar_t max_align_t div_t ldiv_t lldiv_t fpos_t
offsetof va_list stdin stdout stderr errno malloc calloc realloc free abort exit atexit at_quick_exit
quick_exit getenv system bsearch qsort abs labs llabs div ldiv lldiv rand srand
atoi atol atoll atof strtol strtoll strtoul strtoull strtod strtof strtold
mblen mbtowc wctomb mbstowcs wcstombs aligned_alloc remove rename tmpfile tmpnam
fclose fflush fopen freopen setbuf setvbuf fprintf fscanf printf scanf snprintf
sprintf sscanf vfprintf vfscanf vprintf vscanf vsnprintf vsprintf vsscanf fgetc
fgets fputc fputs getc getchar putc putchar puts ungetc fread fwrite fgetpos fseek
fsetpos ftell rewind clearerr feof ferror perror
Text JeetuLocation IntStack text_print text_at text_length stack_get stack_length checked_add checked_sub checked_mul checked_div checked_mod
check_divisor runtime_error stack_push stack_pop stack_top
'''.split())
C_TYPES = {'int': 'int64_t', 'bool': 'bool', 'text': 'Text'}


class Generator:
    """Emit direct C expressions, sequencing only observable operations."""
    def __init__(self, functions=None, result=None):
        self.functions = functions or {}
        self.result = result
        self.loop_scopes = []
        self.lines = []
        self.scopes = []
        self.names = {f.c_name for f in self.functions.values()}
        self.serial = 0
        self.indent = 1

    def emit(self, line=''):
        self.lines.append('    ' * self.indent + line if line else '')

    def fresh(self):
        self.serial += 1
        return f'jeetu_temp_{self.serial}'

    def variable_name(self, source):
        # Reserve the entire compiler namespace and header macro namespace.
        unsafe = (source in C_RESERVED or source.startswith(('_', 'jeetu_'))
                  or source.upper() == source or source.startswith(('int_', 'uint_')))
        base = f'jeetu_user_{source.lstrip("_")}' if unsafe else source
        name = base
        suffix = 2
        while name in self.names:
            name = f'{base}_{suffix}'
            suffix += 1
        self.names.add(name)
        return name

    def lookup(self, token, read=True):
        for scope in reversed(self.scopes):
            if token.text in scope:
                binding = scope[token.text]
                if read:
                    binding.read = True
                return binding
        Parser.fail(token, f'unknown variable {token.text!r}; declare it with मान लो')

    @staticmethod
    def require(token, actual, expected):
        if actual != expected:
            Parser.fail(token, f'expected {expected}, found {actual}')

    @staticmethod
    def helper(name, *arguments):
        return f'{name}({", ".join(arguments)})'

    def temp(self, expr):
        name = self.fresh()
        self.emit(f'{C_TYPES[expr.kind]} {name} = {expr.code};')
        return Expression(expr.kind, name)

    def capture(self, node):
        """Collect an expression's prerequisite statements without emitting them yet."""
        outer = self.lines
        self.lines = []
        expr = self.expression(node)
        lines = self.lines
        self.lines = outer
        return expr, lines

    @staticmethod
    def c_string(value):
        escapes = {34: '\\"', 92: '\\\\', 10: '\\n', 13: '\\r', 9: '\\t'}
        escapes[63] = r'\?'  # Prevent C11 trigraph interpretation.
        return '"' + ''.join(escapes.get(b, chr(b) if 32 <= b < 127 else f'\\{b:03o}')
                             for b in value.encode('utf-8')) + '"'

    def expression(self, node):
        op, t, *args = node
        if op == 'int':
            value = int(t.text)
            if value > 9223372036854775807:
                Parser.fail(t, 'integer literal exceeds signed 64-bit range')
            code = str(value) if value <= 2147483647 else f'INT64_C({value})'
            return Expression('int', code)
        if op == 'bool':
            return Expression('bool', 'true' if t.text == 'सच' else 'false')
        if op == 'str':
            return Expression('text', f'TEXT({self.c_string(args[0])})')
        if op == 'seq':
            Parser.fail(t, '[] is allowed only as a declaration initializer')
        if op == 'var':
            binding = self.lookup(t)
            if binding.kind == 'seq':
                return Expression('seq', binding.reference())
            return Expression(binding.kind, binding.name)
        if op == 'invoke':
            if any(t.text in scope for scope in self.scopes):
                Parser.fail(t, f'{t.text!r} is a variable, not a function')
            function = self.functions.get(t.text)
            if function is None:
                Parser.fail(t, f'unknown function {t.text!r}')
            if len(args[0]) != len(function.parameters):
                Parser.fail(t, f'{t.text} expects {len(function.parameters)} arguments, found {len(args[0])}')
            values = []
            for index, (argument, (_, expected)) in enumerate(zip(args[0], function.parameters)):
                value = self.expression(argument)
                self.require(argument[1], value.kind, expected)
                if value.effect and index < len(args[0]) - 1:
                    value = self.temp(value)
                values.append(value.code)
            return Expression(function.result, f'{function.c_name}({", ".join(values)})', True)
        if op == 'call':
            binding = self.lookup(args[0])
            self.require(t, binding.kind, 'seq')
            if t.text == 'खाली':
                return Expression('bool', f'({binding.name}{"->" if binding.borrowed else "."}len == 0)', True)
            helper = 'stack_pop' if t.text == 'निकालो' else 'stack_top'
            return Expression('int', self.helper(helper, binding.reference()), True)
        if op == 'unary':
            if t.text == '-' and args[0][0] == 'int':
                value = int(args[0][1].text)
                if value == 9223372036854775808:
                    return Expression('int', 'INT64_MIN')
                if value <= 9223372036854775807:
                    literal = str(value) if value <= 2147483647 else f'INT64_C({value})'
                    return Expression('int', f'(-{literal})')
            value = self.expression(args[0])
            self.require(t, value.kind, 'bool' if t.text == '!' else 'int')
            if t.text == '!':
                return Expression('bool', f'(!{value.code})', value.effect)
            return Expression('int', self.helper('checked_sub', '0', value.code), True)
        if op == 'binary':
            left = self.expression(args[0])
            right, prelude = self.capture(args[1])
            operator = t.text
            if operator in ('&&', '||'):
                self.require(t, left.kind, 'bool')
                self.require(t, right.kind, 'bool')
                if prelude:
                    result = self.temp(left)
                    self.emit(f'if ({"!" if operator == "||" else ""}{result.code}) {{')
                    self.lines.extend('    ' + line if line else '' for line in prelude)
                    self.indent += 1
                    self.emit(f'{result.code} = {right.code};')
                    self.indent -= 1
                    self.emit('}')
                    return result
                return Expression('bool', f'({left.code} {operator} {right.code})', left.effect or right.effect)
            self.require(t, right.kind, left.kind)
            if operator in ('==', '!='):
                if left.kind not in ('int', 'bool'):
                    Parser.fail(t, 'equality requires integers or Booleans')
            else:
                self.require(t, left.kind, 'int')
            # C does not sequence function arguments or comparison operands.
            # Snapshot the left operation before any observable right operation.
            if left.effect and (prelude or right.effect):
                left = self.temp(left)
            self.lines.extend(prelude)
            if operator in ('==', '!=', '<', '<=', '>', '>='):
                if args[0][0] == args[1][0] == 'var' and left.code == right.code:
                    # Keep valid self-comparisons warning-free under -Werror.
                    left = self.temp(left)
                return Expression('bool', f'({left.code} {operator} {right.code})', left.effect or right.effect)
            helper = {'+': 'checked_add', '-': 'checked_sub', '*': 'checked_mul',
                      '/': 'checked_div', '%': 'checked_mod'}[operator]
            return Expression('int', self.helper(helper, left.code, right.code), True)
        if op == 'length':
            value = self.expression(args[0])
            if value.kind not in ('seq', 'text'):
                Parser.fail(t, 'लंबाई requires text or an integer sequence')
            helper = 'stack_length' if value.kind == 'seq' else 'text_length'
            return Expression('int', self.helper(helper, value.code), True)
        if op == 'index':
            value = self.expression(args[0])
            if value.kind not in ('seq', 'text'):
                Parser.fail(t, 'indexing requires text or an integer sequence')
            index, prelude = self.capture(args[1])
            self.require(t, index.kind, 'int')
            if value.effect and (prelude or index.effect):
                value = self.temp(value)
            self.lines.extend(prelude)
            helper = 'stack_get' if value.kind == 'seq' else 'text_at'
            kind = 'int' if value.kind == 'seq' else 'text'
            return Expression(kind, self.helper(helper, value.code, index.code), True)
        raise AssertionError(op)

    @staticmethod
    def condition(expr):
        # All compound Boolean expressions are wrapped once by expression().
        code = expr.code
        return code[1:-1] if code.startswith('(') and code.endswith(')') else code

    def braced(self, body):
        self.indent += 1
        self.block(body)
        self.indent -= 1
        self.emit('}')

    def block(self, body, initial=None):
        self.scopes.append(initial or {})
        for node in body:
            op, t, *args = node
            self.emit(f'/* Jeetu {t.line}:{t.col} */')
            if op in ('break', 'continue'):
                if not self.loop_scopes:
                    Parser.fail(t, f'{t.text} is only allowed inside a loop')
                self.cleanup(self.scopes[self.loop_scopes[-1]:])
                self.emit(op + ';')
            elif op == 'return':
                if self.result is None:
                    Parser.fail(t, 'लौटाओ is only allowed inside a function')
                value = self.expression(args[0])
                self.require(t, value.kind, self.result)
                if value.effect and any(binding.kind == 'seq' and not binding.borrowed
                                        for scope in self.scopes for binding in scope.values()):
                    value = self.temp(value)
                self.cleanup(self.scopes)
                self.emit(f'return {value.code};')
            elif op == 'block':
                self.emit('{')
                self.braced(args[0])
            elif op == 'decl':
                if t.text in self.scopes[-1]:
                    Parser.fail(t, 'duplicate declaration in this block')
                name = self.variable_name(t.text)
                if args[0][0] == 'seq':
                    kind = 'seq'
                    self.emit(f'IntStack {name} = {{0}};')
                    for element in args[0][2]:
                        value = self.expression(element)
                        self.require(element[1], value.kind, 'int')
                        self.emit(self.helper('stack_push', '&' + name, value.code) + ';')
                else:
                    value = self.expression(args[0])
                    kind = value.kind
                    if kind not in C_TYPES:
                        Parser.fail(t, 'sequences cannot be copied; initialize with [...]')
                    self.emit(f'{C_TYPES[kind]} {name} = {value.code};')
                self.scopes[-1][t.text] = Binding(kind, name)
            elif op == 'assign':
                binding = self.lookup(t, read=False)
                if binding.kind == 'seq':
                    Parser.fail(t, 'sequence assignment is not supported')
                value = self.expression(args[0])
                self.require(t, value.kind, binding.kind)
                self.emit(f'{binding.name} = {value.code};')
            elif op == 'push':
                binding = self.lookup(t)
                self.require(t, binding.kind, 'seq')
                value = self.expression(args[0])
                self.require(t, value.kind, 'int')
                self.emit(self.helper('stack_push', binding.reference(), value.code) + ';')
            elif op in ('print', 'write'):
                value = self.expression(args[0])
                newline = op == 'print'
                if value.kind == 'text':
                    self.emit(f'text_print({value.code}, {str(newline).lower()});')
                elif value.kind == 'bool':
                    code = f'{value.code} ? "sach" : "jhooth"'
                    self.emit(f'puts({code});' if newline else f'fputs({code}, stdout);')
                elif value.kind == 'int':
                    code = value.code
                    if args[0][0] == 'int' or (args[0][0] == 'unary' and args[0][2][0] == 'int'):
                        code = '(int64_t)' + code
                    suffix = ' "\\n"' if newline else ''
                    self.emit(f'printf("%" PRId64{suffix}, {code});')
                else:
                    Parser.fail(t, 'cannot print a sequence; use a loop')
            elif op in ('if', 'while'):
                if op == 'while':
                    self.loop_scopes.append(len(self.scopes))
                value, prelude = self.capture(args[0])
                self.require(t, value.kind, 'bool')
                if op == 'while' and prelude:
                    self.emit('while (true) {')
                    self.indent += 1
                    self.lines.extend('    ' + line if line else '' for line in prelude)
                    self.emit(f'if (!({self.condition(value)})) break;')
                    self.emit('{')
                    self.braced(args[1])
                    self.indent -= 1
                    self.emit('}')
                else:
                    self.lines.extend(prelude)
                    self.emit(f'{op} ({self.condition(value)}) {{')
                    self.braced(args[1])
                    if op == 'if' and args[2]:
                        self.lines[-1] += ' else {'
                        self.braced(args[2])
                if op == 'while':
                    self.loop_scopes.pop()
        if not returns(body):
            self.cleanup([self.scopes[-1]])
        else:
            # Unreachable declarations are still checked and emitted. Keep them
            # warning-free without duplicating cleanup after an early return.
            for binding in self.scopes[-1].values():
                if not binding.read and not binding.suppressed:
                    self.emit(f'(void){binding.name}; /* Unreachable declaration. */')
        self.scopes.pop()

    def cleanup(self, scopes):
        for scope in reversed(scopes):
            for binding in reversed(list(scope.values())):
                if binding.kind == 'seq' and not binding.borrowed:
                    self.emit(f'free({binding.name}.data);')
                    binding.suppressed = True
                elif not binding.read:
                    self.emit(f'(void){binding.name}; /* Not read on this path. */')
                    binding.suppressed = True


RUNTIME_DIR = pathlib.Path(__file__).with_name('runtime')


def compile_source(source, standalone=True):
    functions, body = Parser(source).parse()
    registry = {}
    allocator = Generator()
    for function in functions:
        name = function.token.text
        if name in registry:
            Parser.fail(function.token, f'duplicate function {name!r}')
        function.c_name = allocator.variable_name(name)
        registry[name] = function

    prototypes, definitions = [], []
    for function in functions:
        if function.result == 'seq':
            Parser.fail(function.token, 'functions cannot return owned sequences')
        generator = Generator(registry, function.result)
        bindings = {}
        parameters = []
        for token, kind in function.parameters:
            if token.text in bindings:
                Parser.fail(token, f'duplicate parameter {token.text!r}')
            name = generator.variable_name(token.text)
            bindings[token.text] = Binding(kind, name, borrowed=kind == 'seq')
            c_type = 'IntStack *' if kind == 'seq' else C_TYPES[kind] + ' '
            parameters.append(f'{c_type}{name}')
        signature = f'{C_TYPES[function.result]} {function.c_name}({", ".join(parameters) or "void"})'
        prototypes.append(signature + ';')
        generator.block(function.body, bindings)
        if not returns(function.body):
            Parser.fail(function.token, 'function must return a value on every path')
        definitions.append(signature + ' {\n' + '\n'.join(generator.lines) + '\n}')

    generator = Generator(registry)
    generator.block(body)
    main = 'int main(void) {\n' + '\n'.join(generator.lines)
    main += '\n\n    return (fflush(stdout) == EOF || ferror(stdout)) ? 1 : 0;\n}\n'
    if standalone:
        header = (RUNTIME_DIR / 'jeetu_runtime.h').read_text()
    else:
        header = '#include "jeetu_runtime.h"\n'
    program = '/* Generated by Jeetu. */\n' + header + '\n'
    if prototypes:
        program += '\n'.join(prototypes) + '\n\n'
    program += main
    if definitions:
        program += '\n' + '\n\n'.join(definitions) + '\n'

    # Keep line mapping out of algorithm bodies and accurate through recursive calls.
    entries = []
    for generated_line, line in enumerate(program.splitlines(), 1):
        match = re.search(r'/\* Jeetu (\d+):(\d+) \*/', line)
        if match:
            entries.append((generated_line, int(match[1]), int(match[2])))
    program += '\n/* Source map for runtime diagnostics; no algorithm logic below. */\n'
    program += 'JeetuLocation jeetu_source_location(int generated_line) {\n'
    if entries:
        program += '    static const struct { int c_line, line, column; } map[] = {\n'
        program += ''.join(f'        {{{c}, {line}, {column}}},\n' for c, line, column in entries)
        program += '    };\n    size_t index = 0;\n'
        program += '    while (index + 1 < sizeof(map) / sizeof(map[0]) && map[index + 1].c_line <= generated_line)\n        ++index;\n'
        program += '    return (JeetuLocation){map[index].line, map[index].column};\n}\n'
    else:
        program += '    (void)generated_line;\n    return (JeetuLocation){1, 1};\n}\n'
    if standalone:
        runtime = (RUNTIME_DIR / 'jeetu_runtime.c').read_text().replace('#include "jeetu_runtime.h"\n', '', 1)
        program += '\n/* Embedded runtime for single-file export. */\n' + runtime
    return program


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=f'Jeetu {__version__}')
    parser.add_argument('command', choices=['check', 'emit-c', 'build', 'run'])
    parser.add_argument('source', type=pathlib.Path)
    parser.add_argument('-o', '--output', type=pathlib.Path)
    parser.add_argument('--cc', default='cc', help='C compiler executable (default: cc)')
    parser.add_argument('--standalone', action='store_true', help='embed runtime support in generated C')
    args = parser.parse_args()
    try:
        code = compile_source(args.source.read_text(encoding='utf-8'), standalone=args.standalone)
        if args.command == 'check':
            print(f'{args.source}: OK')
            return 0
        if args.command == 'emit-c':
            if args.output:
                args.output.write_text(code, encoding='utf-8')
            else:
                print(code, end='')
            return 0
        with tempfile.TemporaryDirectory(prefix='jeetu-') as directory:
            output = (args.output or pathlib.Path('a.out')).resolve() if args.command == 'build' else pathlib.Path(directory) / 'program'
            cfile = pathlib.Path(str(output) + '.c') if args.command == 'build' else pathlib.Path(directory) / 'program.c'
            if args.command == 'build' and args.source.resolve() in (output, cfile.resolve()):
                raise Error('output paths must not overwrite the source file')
            cfile.write_text(code, encoding='utf-8')
            command = [args.cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', str(cfile)]
            if not args.standalone:
                command += ['-I', str(RUNTIME_DIR), str(RUNTIME_DIR / 'jeetu_runtime.c')]
            result = subprocess.run(command + ['-o', str(output)])
            if result.returncode:
                print('Jeetu backend failure: C compilation failed', file=sys.stderr)
                return 1
            if args.command == 'run':
                return subprocess.run([str(output)]).returncode
        return 0
    except Error as error:
        print(f'{args.source}:{error}', file=sys.stderr)
        return 1
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        print(f'jeetu: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
