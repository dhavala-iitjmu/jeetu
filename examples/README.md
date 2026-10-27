# Jeetu example guide

All examples use Devanagari language constructs and English variable/function
names. Run them from the repository root:

```sh
python3 jeetu.py run examples/fibonacci-recursive.jeetu
```

Build any example to inspect its C:

```sh
mkdir -p build
python3 jeetu.py build examples/maximum.jeetu -o build/maximum
./build/maximum
# Read build/maximum.c; runtime implementation is in runtime/jeetu_runtime.c.
```

Each example has a matching `.expected` file. The test suite discovers every
`.jeetu` file here, compiles it with strict C warnings and verifies exact output.
The output column below separates successive lines with `;`.

| Example | What it teaches | Expected output |
| --- | --- | --- |
| [factorial](factorial.jeetu) | Variables, multiplication, while loop | `120` |
| [gcd](gcd.jeetu) | Euclid's algorithm and remainder | `6` |
| [fibonacci-recursive](fibonacci-recursive.jeetu) | Typed function, base case, two recursive calls | `55` |
| [fibonacci-iterative](fibonacci-iterative.jeetu) | Same result with a loop and constant storage | `55` |
| [maximum](maximum.jeetu) | Borrowed integer sequence, indexing, negative values | `-3; 5` |
| [reverse-string](reverse-string.jeetu) | Text indexing and output without newline | `!uteeJ ,olleH` |
| [prime](prime.jeetu) | Boolean return, early return, trial division | `sach; jhooth; jhooth` |
| [search-break](search-break.jeetu) | Linear search with `रुको` | `3` |
| [sum-continue](sum-continue.jeetu) | Skip nonpositive values with `जारी` | `14` |
| [binary](binary.jeetu) | Stack reversal and base conversion | `101010` |
| [power-recursive](power-recursive.jeetu) | Exponentiation by squaring | `1024; 1` |
| [mutual-recursion](mutual-recursion.jeetu) | Forward calls between two functions | `sach; jhooth` |
| [text-functions](text-functions.jeetu) | Text parameters/returns and Unicode code points | `J; 3; 🙂` |
| [tape](tape.jeetu) | Two stacks simulating a tape, state transitions | `1; 1; 1; 1` |

## The three requested algorithms

### Recursive Fibonacci

`fibonacci-recursive.jeetu` implements the recurrence directly. Input is assumed
nonnegative. The simple recursive algorithm repeats work and is suitable for
small examples. Compare it with `fibonacci-iterative.jeetu`; both compute `F(10)`.
Checked 64-bit arithmetic bounds both implementations; they are not
arbitrary-precision calculators. The iterative version can compute through
`F(92)`; `F(93)` overflows. Recursion becomes impractically slow much earlier.

### Maximum of an integer array

Jeetu's integer sequence is a growable, zero-indexed array with stack operations.
`maximum.jeetu` takes it as a borrowed `सूची` parameter and reads `values[i]`.
It starts from the first element, not zero, so all-negative inputs work.
The precondition is a nonempty sequence: an empty input produces a bounds error.
The second printed line confirms the input still has five elements afterward.

### Reverse a string

`reverse-string.jeetu` walks backward through a text value and prints each
character using `लिखो`, followed by an empty `बोलो` to finish the line. It does
not construct a new reversed text value; text concatenation is not implemented.
Indexing counts Unicode code points. Reversing combining marks or multi-code-point
emoji does not preserve visual grapheme clusters; the example deliberately uses
ASCII. `text-functions.jeetu` separately illustrates Unicode indexing.

The power and mutual-recursion examples also assume nonnegative inputs.

## Suggested exercises

- Run recursive and iterative Fibonacci for inputs 0 through 15 and compare.
- Change `maximum` to find the minimum; test duplicates and a one-element input.
- Change the search target to a missing value and verify the output is `-1`.
- Remove `जारी` by rewriting the positive-sum loop with an `अगर` block.
- Change binary conversion to print octal digits and test zero.
- Trace one iteration of the tape simulation in the emitted C.

Use `--standalone` with `emit-c` when you want the runtime embedded in one file.
Otherwise manual C compilation needs `-I runtime` and `runtime/jeetu_runtime.c`;
`build` and `run` arrange this automatically.
