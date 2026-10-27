# From Jeetu source to a native executable

Start with `examples/fibonacci-recursive.jeetu`. Run it, then build it:

```sh
mkdir -p build
python3 jeetu.py run examples/fibonacci-recursive.jeetu
python3 jeetu.py build examples/fibonacci-recursive.jeetu -o build/fibonacci-recursive
./build/fibonacci-recursive
```

All print `55` when executed. Inspect `build/fibonacci-recursive.c`: it contains function
prototypes, `main`, a readable `fib` definition, and source-mapping metadata.
The runtime implementation is separate in `runtime/jeetu_runtime.c`.

## Implementation map

1. `lex` recognizes tokens with source line/column locations. Complete Unicode
   words are scanned; only Devanagari keywords or ASCII identifiers are accepted.
2. `Parser` builds a list of `Function` records and a main-body syntax tree.
   Statements use recursive descent; expressions use precedence climbing with
   postfix indexing. Parameters and return types are explicit.
3. `compile_source` collects all function signatures first. This permits forward
   and mutually recursive calls. Each function is checked in an independent
   scope, then main is checked. Conservative return-path analysis rejects
   functions that could reach the end without returning a value.
4. `Generator` checks bindings and types while generating C. Safe source names
   remain unchanged; C/header/runtime collisions and shadowing get distinct names.
   Its expression records carry C text and whether evaluation is observable.
5. C expressions and `while`/`if` statements remain direct where possible.
   Temporaries sequence function arguments, stack reads/mutations and competing
   failures. C `&&`/`||` handle short-circuiting unless the right operand needs
   prerequisite statements, in which case an explicit conditional block is used.
6. Scope metadata tracks owned sequences and borrowed parameters. Return, break
   and continue release exactly the owned sequences whose blocks are exited.
   A return expression is evaluated before releasing any storage it might read.
7. The CLI emits C and invokes a C11 compiler without a shell. Default builds
   automatically add the runtime include directory and source file. `run` uses
   temporary build files; `build` retains the intermediate `.c`.

To inspect tokens and syntax trees:

```sh
python3 - <<'PY'
from pathlib import Path
from pprint import pprint
from jeetu import lex, Parser
source = Path('examples/fibonacci-recursive.jeetu').read_text()
pprint(lex(source))
functions, main = Parser(source).parse()
pprint(functions)
pprint(main)
PY
```

## Reading the generated C

An update looks like `factorial = checked_mul(factorial, n);`. Plain C signed
multiplication can overflow with undefined behavior, so a small runtime function
checks first. The source program does not need explicit checks or extra numeric
location arguments. The header macro evaluates each operand exactly once and
passes diagnostic location metadata to the runtime function.

The generated `jeetu_source_location` table maps generated C lines to Jeetu
statements. Location values are passed by value; recursive calls cannot overwrite
a caller's error location. This removes the earlier `set_source_location` calls
from algorithm bodies. The table is below the program's functions, not interleaved
with the algorithm. Editing generated C lines can invalidate this mapping;
edit Jeetu and regenerate when accurate diagnostics matter.

`jeetu_temp_*` names appear only where evaluation order or strict C warnings
require them. For example, the result of the first recursive Fibonacci call is
saved before the second call. `(void)name` is used selectively for variables or
parameters not read on an exit path, so strict-warning builds accept valid source.
Ordinary variables such as `n` and `factorial` are preserved. Shadowed bindings
may become `x_2`; this also avoids C's different declaration-initializer scope.

Sequences appear as `IntStack`; borrowed parameters become `IntStack *` in C.
The Jeetu programmer does not manage these pointers. Bounds-checked indexing
uses `stack_get`. Immutable text is a `Text` view with a pointer and byte count;
`TEXT("hello")`, `text_at` and `text_print` provide literal construction, Unicode
code-point indexing and output without copying or allocating text.

The generated C is intended to be understandable, not necessarily the shortest
possible C. Bounds checks, overflow checks, ownership cleanup and sequencing
remain explicit where the language semantics require them.

## Linking or exporting a standalone file

Default emitted C is small and uses the reusable runtime:

```sh
python3 jeetu.py emit-c examples/maximum.jeetu -o build/maximum.c
cc -std=c11 -Wall -Wextra -Werror -pedantic \
   -I runtime build/maximum.c runtime/jeetu_runtime.c -o build/maximum
```

For distribution without separate runtime files:

```sh
python3 jeetu.py emit-c examples/maximum.jeetu --standalone -o build/maximum-standalone.c
cc -std=c11 -Wall -Wextra -Werror -pedantic \
   build/maximum-standalone.c -o build/maximum-standalone
```

Standalone export embeds the full small runtime. `compile_source(source)` also
returns standalone C by default for programmatic use and tests; pass
`standalone=False` to get the linked form used by the default CLI.

## Adding a language feature

1. Define its syntax, types, evaluation order, lifetime and error cases in the
   specification. Prefer general language constructs to a helper per algorithm.
2. Add tokens/AST nodes and semantic checks. Reject invalid programs before C
   compilation. Reserve any new C runtime names against source-name collisions.
3. Generate readable C and put reusable support in the runtime. Preserve
   left-to-right evaluation and avoid C undefined behavior.
4. Add executable examples with `.expected` output and tests for incorrect use.
   Exercise ownership transfers and failures as well as successful computation.

## Verification and limits

Tests compile and execute all examples against exact expected output. Additional
cases cover precedence, lexical scope, recursion, forward calls, borrowed aliases,
returns, break/continue cleanup, Unicode and embedded-zero text, bounds, stack
growth, observable evaluation order, short-circuiting, arithmetic failures,
rejected programs, and both linked and standalone CLI workflows.

Set `SANITIZE=1` to enable AddressSanitizer and UndefinedBehaviorSanitizer in
execution tests. `CC` selects their compiler; CLI tests also exercise default
`cc`. Deterministic allocation-failure injection and call-stack exhaustion remain
future work. This is an educational compiler, not a hardened runtime for hostile
inputs. Unicode text indexing does not implement grapheme-cluster segmentation.
