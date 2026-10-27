# Jeetu: language design and development goals

## Purpose

Jeetu is a proposed small programming language intended to make programming and language implementation approachable and enjoyable. It takes inspiration from the Hinglish syntax of [Bhailang](https://github.com/DulLabs/bhai-lang), with a patient teacher's tone inspired by Jeetu Bhaiya from *Kota Factory*.

Jeetu programs will compile into readable C, which an existing C compiler will compile into native executables. Students should be able to inspect each stage and extend the language themselves.

This document is a design brief, not a claim that the language or compiler already exists. Syntax examples are proposals. This is an independent educational project; no affiliation or endorsement is implied.

## Goals

- Provide a small, consistent language with short, memorable Hinglish keywords.
- Generate readable C that connects language features to familiar programming concepts.
- Define behaviour precisely, including errors, evaluation order and memory limits.
- Design an abstract computational model that is Turing complete, and document a constructive justification.
- Make the compiler understandable enough for students to add a feature and test it.
- Keep the first implementation small enough to inspect and explain as a whole.

The first release does not need classes, generics, concurrency, a package manager, an optimiser or compatibility with arbitrary C libraries. It also does not need to reproduce every feature of C.

## Proposed experience

A possible program:

```text
shuru {
    maan lo n = 5;
    maan lo factorial = 1;

    jab tak (n > 1) {
        factorial = factorial * n;
        n = n - 1;
    }

    bolo factorial;
}
```

Expected output:

```text
120
```

The intended toolchain is:

```text
program.jeetu
    -> lexer and parser
    -> syntax tree
    -> name and type checking
    -> generated C + Jeetu runtime
    -> C compiler
    -> executable
```

Possible command-line interface, to be implemented:

```sh
jeetu check program.jeetu
jeetu emit-c program.jeetu -o program.c
jeetu build program.jeetu -o program
jeetu run program.jeetu
```

`emit-c` should preserve a useful connection between the source program and the generated code. Generated C may call runtime helpers; it need not be a literal line-for-line translation.

## Language design principles

1. **Short syntax.** Avoid requiring a long dialogue or catchphrase for every operation.
2. **One meaning per construct.** Do not introduce several interchangeable keywords in the first version.
3. **Explicit semantics.** Specify behaviour before implementing a feature.
4. **Useful diagnostics.** Identify the source location, explain the error and suggest a concrete correction where possible.
5. **Visible compilation.** Let students inspect tokens, the syntax tree and generated C.
6. **Consistent behaviour.** Generated C must implement Jeetu's rules rather than accidentally inherit undefined C behaviour.

Use ASCII identifiers and keywords initially. Strings may contain UTF-8 text, with their supported operations specified separately. Define how multiword keywords such as `maan lo` and `jab tak` are tokenised, including whitespace and identifier boundaries.

## Initial feature set

| Feature | Role |
| --- | --- |
| Integer and Boolean values | Arithmetic and conditions |
| Variables and assignment | Mutable program state |
| Arithmetic and comparisons | Computation and decisions |
| `agar` and `warna` | Conditional execution |
| `jab tak` | Conditional repetition |
| Input and `bolo` output | Standalone programs |
| Functions and return values | Decomposition and recursion |
| A growable sequence | Data whose size is determined during execution |
| String literals | Messages and simple output |

Only `shuru`, `maan lo`, `jab tak` and `bolo` are illustrated above. Function, input and sequence syntax remain to be designed. Do not treat this list as a final grammar.

Start with a single program file and lexical block scope. Prefer static types inferred from initialisers, with explicit parameter and return types when functions are added. A variable's type should remain fixed after declaration.

## Semantic decisions to settle

Before implementation, write a short specification covering:

- Operator precedence and associativity.
- Left-to-right evaluation and short-circuit Boolean operators.
- Whether conditions must be Boolean; the proposed default is yes.
- Declaration, shadowing and use-before-declaration rules.
- Integer representation, division, remainder and overflow behaviour.
- Input parsing, invalid input and end-of-file behaviour.
- Output spacing, Boolean representation and trailing newlines.
- Function arguments, return types, recursion and variable lifetime.
- Sequence ownership, assignment, growth and bounds checking.
- Runtime failures and process exit status.

A practical initial integer type is a signed 64-bit integer with checked arithmetic. Overflow and division by zero should produce errors rather than wrap silently or invoke undefined behaviour. Specify division as truncation toward zero and handle the minimum-integer divided by minus-one case explicitly.

Fixed-width integers alone do not provide unbounded state. The Turing-completeness argument must therefore use the storage model described below, not assume that integer variables can grow without limit.

## Turing completeness

Compiling into C does not by itself establish that Jeetu is Turing complete. Neither does merely having a loop construct.

The abstract language must support computation with potentially unbounded storage. Every physical implementation is limited by available memory and time; this is separate from the mathematical property of the language model.

A proposed constructive route is to support growable sequences with append, remove-last, empty-test and last-element operations. Two such sequences can represent the cells to the left and right of a Turing-machine head, with the current cell stored separately. Each cell needs only a symbol from a finite alphabet.

A simulation step can:

1. Inspect the current state and current symbol.
2. Select the applicable transition using conditionals.
3. Write the new symbol and update the state.
4. Move the head by transferring a symbol between the two sequences, treating an empty side as blank tape.
5. Repeat until a halt state is reached.

The specification must allow these sequences to grow without a language-defined bound in the abstract model. It must not require an unbounded position to fit in a fixed-width integer. An implementation may reject further growth when allocation or representation limits are reached, with a clear resource-exhaustion error.

The proof obligation is to show how an arbitrary machine's finite transition table and each of its steps are represented by Jeetu constructs. An executable simulator and tests support that argument but do not replace it. Factorial, Fibonacci and an infinite loop are examples of programs, not proofs of universality.

Functions and recursion are useful teaching features, but they are not required for this particular construction.

## Compiler and runtime

Use a real lexer and parser rather than keyword replacement. Text substitution will not reliably handle strings, comments, nested blocks, precedence or scope.

A suitable small architecture is:

- **Lexer:** tokens and source spans.
- **Parser:** syntax tree; recursive descent with a precedence-based expression parser is a reasonable starting point.
- **Semantic analysis:** declarations, scope, types and return checks.
- **C generator:** readable C, generated identifiers that cannot collide with runtime names, and source-location information.
- **Runtime:** checked arithmetic, input/output, sequence operations and error reporting.
- **Driver:** compiler invocation, build output and exit-status handling.

Target portable C11 initially. Do not rely on the host C compiler's expression evaluation order to implement Jeetu's evaluation order; emit temporaries where necessary. Check arithmetic before performing operations that could be undefined in C.

The compiler implementation language is an open choice. Writing it in C would fit a C course and expose memory management directly. Python could make the first compiler easier to read and modify. Either can generate C; the implementation language and compilation target are independent decisions.

Keep memory ownership simple and documented. Raw pointers and manual `free` should not be part of the initial Jeetu surface language. Define how sequence values are passed and copied before implementing functions that use them.

## Diagnostics and personality

The language can use a friendly teacher's tone without obscuring the technical explanation. For example:

```text
program.jeetu:8:10: total has not been given a value.
Assign a value before using it here.
```

Any Hinglish wording should remain brief and understandable. Keep the location, error category and correction clear. Personality should not depend on reproducing dialogue from a show.

## Development milestones

### 1. Specify the smallest executable subset

Freeze a grammar for blocks, integer literals, variables, arithmetic and output. Define their semantics and provide valid and invalid examples.

**Completion:** the specification determines what each example does, and which examples are rejected.

### 2. Compile the first programs

Implement tokenisation, parsing, basic semantic checks and C generation. Compile and execute generated C with an existing compiler.

**Completion:** arithmetic and variable programs produce verified output; malformed programs produce source-located errors.

### 3. Add control flow

Implement comparisons, Boolean values, conditionals and loops.

**Completion:** factorial, Euclid's algorithm and nested-loop examples work; overflow and invalid operations fail as specified.

### 4. Add dynamic storage and establish the computational model

Specify and implement the growable-sequence operations needed for tape simulation. Document the abstract unbounded model and the implementation's resource limits.

**Completion:** provide the machine-simulation construction, representative executable examples and a reviewed argument for Turing completeness.

### 5. Add functions and practical input

Implement typed parameters, return values, recursion and documented input behaviour. Settle sequence ownership and function-call behaviour first.

**Completion:** iterative and recursive examples agree where expected; invalid inputs and invalid calls have predictable diagnostics.

### 6. Package for teaching

Provide installation instructions, a language guide, annotated examples and an explanation of each compilation stage.

**Completion:** a student can run a program, inspect its generated C, and follow a guide to add and test one small feature.

## Verification

- Test lexing of keyword-like identifiers, strings and comments.
- Test precedence, nesting, scope and rejected syntax.
- Check generated programs against independently determined outputs.
- Test negative numbers, arithmetic boundaries, invalid input and division by zero.
- Test sequence growth, empty operations, bounds and allocation failure handling.
- Test evaluation order using expressions with observable effects once such expressions exist.
- Compile generated C with strict warnings and, where available, both GCC and Clang.
- Use sanitizers during development to detect memory and undefined-behaviour defects.
- Preserve regression tests for every corrected compiler bug.

The compiler should diagnose language errors before C compilation. If the C compiler rejects generated code, distinguish a compiler/backend failure from a Jeetu source error.

## Educational use

A student extension should require four concrete steps:

1. Define the syntax and meaning of a small feature.
2. Extend the parser and semantic checks.
3. Generate the corresponding C and any required runtime support.
4. Test both valid use and incorrect use.

This connects language design to the course's existing topics: strings, structures, functions, recursion, pointers and dynamic memory. The primary learning outcome is understanding how a precise language specification becomes an executable implementation.

## First decisions for this repository

- Choose the compiler implementation language.
- Agree on the smallest grammar and the exact integer/Boolean semantics.
- Select the initial sequence operations and ownership rules.
- Write a few reference programs and expected diagnostics.
- Implement the first end-to-end compilation path before adding more keywords.
