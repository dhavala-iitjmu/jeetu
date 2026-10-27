# Jeetu 0.1 language specification

This document defines the implemented language. The compiler produces C11;
`build` and `run` automatically link its runtime into a native executable.

## Source and keywords

Source files are UTF-8. Identifiers match `[A-Za-z_][A-Za-z_0-9]*` and are
case-sensitive. Keywords use Devanagari exclusively. Unicode remains allowed in
text literals and comments. Whole words are scanned before keyword matching:
`शुरूआत` is rejected as a non-ASCII identifier, not split into tokens.

| Keyword | Meaning |
| --- | --- |
| `शुरू` | Main program block |
| `मान लो` | Variable declaration |
| `कार्य` | Function declaration |
| `लौटाओ` | Return a value |
| `पूर्णांक`, `बूलियन`, `पाठ`, `सूची` | Integer, Boolean, text, integer-sequence types |
| `अगर`, `वरना` | If and else |
| `जब तक` | While loop |
| `रुको`, `जारी` | Break and continue |
| `बोलो`, `लिखो` | Output with and without newline |
| `सच`, `झूठ` | Boolean literals |
| `डालो`, `निकालो`, `आखिरी`, `खाली` | Push, pop, top, empty-test |
| `लंबाई` | Text or sequence length |

Each keyword word is reserved individually. Romanized words such as `shuru` are
ordinary identifiers, not aliases. Whitespace (Python Unicode `\s`) separates
tokens; `//` comments extend to newline. Multiword keywords may be separated by
whitespace or comments. Block comments are unsupported. Operators use longest
matching. Source lines and columns are one-based; columns count Unicode code
points, with tabs counting as one character. LF separates lines; file reading
normalizes CRLF.

Integer literals use ASCII decimal digits; leading zeroes remain decimal.
Double-quoted strings use JSON escapes, including `\uXXXX`. Raw controls,
raw newlines and unpaired surrogates are rejected. Valid surrogate pairs decode
to Unicode scalar values. Embedded zero bytes are supported.

## Grammar

Here `{ X }` means repetition, `[ X ]` means optional syntax, and quoted
terminals are literal tokens. Precedence is specified separately.

```ebnf
program     = { function }, "शुरू", block, EOF ;
function    = "कार्य", identifier, "(", [ parameters ], ")", ":", type, block ;
parameters  = parameter, { ",", parameter } ;
parameter   = identifier, ":", type ;
type        = "पूर्णांक" | "बूलियन" | "पाठ" | "सूची" ;
block       = "{", { statement }, "}" ;
statement   = block
            | "मान", "लो", identifier, "=", expression, ";"
            | identifier, "=", expression, ";"
            | ("बोलो" | "लिखो" | "लौटाओ"), expression, ";"
            | ("रुको" | "जारी"), ";"
            | "अगर", "(", expression, ")", block, [ "वरना", block ]
            | "जब", "तक", "(", expression, ")", block
            | "डालो", "(", identifier, ",", expression, ")", ";" ;
expression  = primary | unary-op, expression
            | expression, binary-op, expression ;
primary     = atom, { "[", expression, "]" } ;
atom        = integer | "सच" | "झूठ" | string | identifier
            | "(", expression, ")"
            | "[", [ arguments ], "]"
            | identifier, "(", [ arguments ], ")"
            | stack-op, "(", identifier, ")"
            | "लंबाई", "(", expression, ")" ;
arguments   = expression, { ",", expression } ;
stack-op    = "खाली" | "आखिरी" | "निकालो" ;
unary-op    = "-" | "!" ;
```

Sequence literals are permitted only as declaration initializers, optionally
parenthesized; each element must be an integer. Functions cannot return `सूची`.
There are no general expression statements, void functions, default arguments,
function values, closures, globals or implicit conversions.

## Types, bindings and scope

Declarations infer a fixed type from their initializer: integer, Boolean, text
or integer sequence. Every variable is initialized. Duplicate declarations in a
block and uses before declaration are errors. Every block introduces lexical
scope; inner variables may shadow outer ones. In `मान लो x = x + 1;`, the
initializer sees the outer `x`, if any; the new binding becomes visible afterward.
Each loop iteration creates fresh body-local bindings.

Integers range from −9223372036854775808 through 9223372036854775807. Positive
literals must fit. Unary minus directly applied to literal 9223372036854775808
is the minimum integer, including when parenthesized. Otherwise that magnitude
is rejected. Booleans are `सच` and `झूठ`.

Text is immutable UTF-8 backed by program-lifetime literals. Assignment, argument
passing and returns copy a view, not character storage. Character indexing also
returns an immutable view, so returning it from a function cannot dangle.
There is no concatenation, mutation, input-created text or allocation for text.

## Functions and returns

```text
कार्य square(n: पूर्णांक): पूर्णांक {
    लौटाओ n * n;
}
शुरू { बोलो square(7); }
```

Functions are top-level, precede `शुरू`, and have unique names. All signatures
are collected before checking bodies: forward calls, recursion and mutual
recursion are supported. Each parameter has an explicit type, and the return
type is explicit. Argument counts and types must match exactly. Arguments
evaluate left to right. Integer, Boolean and text parameters are passed by value;
reassigning them does not change the caller's variable.

Sequence parameters borrow the caller's sequence by reference. Push/pop changes
are visible to the caller, which remains the owner. Passing the same sequence
to multiple parameters is allowed; these parameters alias the same storage.
No reference escapes because functions cannot return or copy sequences. Borrowed
parameters are never freed by the callee. Local sequences are freed on normal
block exit and on return, break or continue that exits their declaring blocks.

Parameters share the function's outermost body scope. Function bodies cannot
access variables from `शुरू` or other functions. A local variable may shadow a
function name, but cannot then be called. Functions have no mutable global state.

`लौटाओ expression;` evaluates its value, releases owned local sequences, and
returns to the caller. It is invalid in `शुरू`. Every function must visibly
return on all paths: a return statement, a returning nested block, or an if/else
whose two branches return establishes this. Loops alone do not establish return,
even if their condition is literally true. All source is checked, including
unreachable statements. Recursion uses the native call stack; excessive depth
can exhaust host resources without a Jeetu diagnostic. No tail-call guarantee
or fixed language-level recursion bound is provided.

## Expressions and arithmetic

From lowest to highest precedence:

| Operators | Operands | Result |
| --- | --- | --- |
| `\|\|`, then `&&` | Booleans | Boolean |
| `==`, `!=` | Two integers or two Booleans | Boolean |
| `<`, `<=`, `>`, `>=` | Integers | Boolean |
| `+`, `-` | Integers | Integer |
| `*`, `/`, `%` | Integers | Integer |
| unary `-`, `!` | Integer / Boolean | Integer / Boolean |
| indexing `[]` | Sequence/text and integer index | Integer / text |

Binary operators associate left, unary operators right. Parentheses override
precedence. Comparisons do not chain mathematically; `1 < 2 < 3` is a type error.
Text and sequences cannot be compared. Array element assignment is unsupported.

Operands evaluate left to right. `&&` skips the right operand if the left is
false; `||` skips it if the left is true. Skipped operands still type-check.
The compiler introduces temporaries only where observable effects or strict C
warnings require them. Function calls, checked operations and stack reads can
be observable, including the order of runtime failures.

Arithmetic is checked before potentially undefined C operations. Overflow and
zero division fail at runtime. Division truncates toward zero; nonzero remainder
has the dividend's sign. Both `/` and `%` fail for minimum integer with divisor
−1. This is intentional even though the mathematical remainder would be zero.

## Control flow and output

Conditions must be Boolean. `अगर` selects one branch; `वरना` is optional.
`जब तक` checks its condition before every iteration. `रुको` exits the innermost
loop. `जारी` skips to that loop's next condition evaluation. Both are rejected
outside a loop in the same function. Nested blocks' owned sequences are released
on these transfers; storage belonging to enclosing blocks remains alive.

`बोलो` prints a value followed by LF; `लिखो` adds no newline. Integers print in
decimal, Booleans as `sach` / `jhooth`, text as UTF-8 bytes. No extra spaces are
inserted. Text output preserves embedded zero bytes. Sequences require a loop to
print elements. Detected standard-output errors produce status 1 at final flush.

## Integer sequences and text indexing

```text
मान लो values = [4, 9, -2];
बोलो values[1];       // 9
बोलो लंबाई(values);  // 3
डालो(values, 7);
बोलो निकालो(values); // 7
मान लो word = "A🙂é";
बोलो लंबाई(word);    // 3 code points
बोलो word[1];        // 🙂
```

Sequence literals create fresh owned storage; elements evaluate and append left
to right. `डालो` appends an integer. `निकालो` removes and returns the last
integer; `आखिरी` returns it without removing it. Both fail on empty sequences.
`खाली` tests emptiness. These stack operations require a sequence variable.

`value[index]` reads an element or a one-code-point text view. Indices are
zero-based signed integers. Negative and out-of-range indices fail. `लंबाई`
returns the element/code-point count, failing if it cannot fit in a Jeetu integer.
Text indexing scans UTF-8 and counts Unicode scalar values, not bytes or grapheme
clusters. Combining marks and complex emoji can occupy multiple indices.

Sequences cannot be assigned, copied or returned. Only parameter borrowing can
create aliases. Removed elements need not release capacity. Physical storage is
a contiguous allocation tracked by `size_t`; capacity doubles on demand up to
`SIZE_MAX / sizeof(int64_t)`. Allocation/capacity failure produces a runtime error.
The abstract model allows arbitrarily large finite sequences, with no fixed
language length bound. Indexed access and length are conveniences: the
Turing-completeness construction uses push, pop and empty-test without fitting
an unbounded position into a fixed-width integer.

## Compilation, diagnostics and resource limits

`check`, successful emission/building and successful programs return 0. Handled
source, runtime, backend and driver failures return 1; CLI usage errors return 2.
`run` propagates executable status, subject to host signal conventions. OS memory
limits and stack exhaustion may terminate a process without a runtime diagnostic.
Excessively nested source can exceed the Python compiler's recursion limit.

Front-end errors include filename, line and column. Runtime diagnostics identify
the enclosing Jeetu statement/condition (binding name for declarations and
assignments, sequence name for push). Runtime macros pass a source location by
value through a generated C-line map. Recursive calls cannot overwrite it. No
recovery is attempted; process-ending failures let the OS reclaim storage.

Default emitted C includes `jeetu_runtime.h`; compile with `-I runtime` and link
`runtime/jeetu_runtime.c`. `build`/`run` do this automatically. `--standalone`
embeds the runtime for single-file distribution. `build -o PATH` retains `PATH.c`;
`emit-c -o PATH` writes only C to the requested path. C11 with `int64_t` is required.
Safe source names are preserved; conflicting or shadowed names are renamed.
Source comments and diagnostic mapping are generated; manually inserting C lines
can make diagnostic mappings stale. Regenerate C after editing Jeetu source.
C compiler failures are distinguished from Jeetu source errors. Compiler commands
use argument arrays, not shell strings.
