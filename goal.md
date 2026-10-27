# Jeetu: purpose and development goals

Jeetu is an educational language that compiles to readable C11 and native
executables. Students should be able to follow tokenization, parsing, semantic
checks, C generation and execution, then add a small feature themselves.

The [README](README.md) is the entry point, the [specification](docs/spec.md)
defines current behavior, and the [workflow](docs/workflow.md) explains how it
is implemented. The [example guide](examples/README.md) provides algorithms
and expected results.

## Design principles

- Devanagari constructs and ASCII English identifiers should be visually distinct.
- Specify semantics before implementation, especially evaluation order, overflow,
  scope, ownership and resource limits.
- Preserve readable names and ordinary control flow in generated C. Keep reusable
  runtime code separate by default; provide explicit standalone export.
- Keep the direct `.jeetu` → executable workflow simple: build and linking are
  compiler responsibilities, not tasks students must repeat manually.
- Add general constructs such as functions rather than a built-in per algorithm.
- Diagnose source errors before C compilation and keep messages useful to learners.
- Distinguish abstract computational power from finite hardware resources.

## Implemented foundation (0.1)

- A Python lexer/parser, type checking and readable C11 generation.
- Checked integers, Booleans and immutable UTF-8 text.
- Owned growable integer sequences, literals, indexing and length operations.
- Functions with typed parameters/returns, recursion, forward and mutual calls.
- Borrowed sequence parameters and automatic cleanup across return/loop transfers.
- If/else, while, break and continue; output with or without newline.
- A separate reusable runtime and optional standalone C export.
- Fourteen executable examples with expected outputs and regression tests.

The [Turing-completeness construction](docs/turing-completeness.md) uses two
abstractly unbounded stacks. Functions, indexed access and text make programs
more convenient, but are not needed for that construction.

## Next milestones

1. **Input:** specify parsing, invalid input and EOF behavior; preserve clear
   ownership rules if text becomes dynamically allocated.
2. **Text and collection extensions:** consider concatenation, mutable indexed
   access and more sequence types only with explicit lifetime/type rules.
3. **Runtime verification:** deterministic allocator-failure injection and checks
   with distinct GCC and Clang toolchains, including more resource-limit cases.
4. **Teaching material:** annotated exercises that change syntax, semantic checks,
   generated C and tests together.

Floating point, structs/classes, raw pointers, manual memory management, file I/O,
modules, closures, concurrency and a package manager remain outside this subset.

## Verification expectations

Compare programs against independently determined outputs; reject malformed
syntax, invalid names/types and missing return paths. Cover bounds, overflow,
empty operations, scope, aliases, recursion, early exits and evaluation order.
Compile with strict warnings and use sanitizers where available. Preserve a
regression test for each corrected compiler defect.

Independent educational project inspired by Hinglish programming and a patient
teacher's tone; no affiliation or endorsement is implied. Personality must not
obscure technical explanations.
