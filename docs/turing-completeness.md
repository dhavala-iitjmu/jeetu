# Why the abstract Jeetu language is Turing complete

The claim applies to the specified abstract language with arbitrarily growable
sequences. It does not claim that a finite computer has infinite memory.
Checked 64-bit integers alone, loops alone, and compiling to C do not establish
Turing completeness.

## Representing a tape

Fix a deterministic Turing machine with a finite tape alphabet, finite set of
states, a blank symbol, and left/right moves. At any finite step only finitely
many tape cells have been visited. Use two sequences and a current-cell value:

- `left` holds cells left of the head, nearest cell at the top.
- `right` holds cells right of the head, nearest cell at the top.
- `cell` holds the symbol under the head.

Everything beyond the stored cells is blank. A written blank may be stored
explicitly; this changes no observable tape symbol.

For alphabets and states with small integer encodings, a transition that writes
symbol `w`, enters state `q`, and moves right is translated as:

```text
cell = w;
state = q;
डालो(left, cell);
अगर (खाली(right)) { cell = 0; }
वरना { cell = निकालो(right); }
```

Here `w` and `q` are replaced with literal encodings, and `0` denotes blank.
A left move swaps the roles of `left` and `right`:

```text
cell = w;
state = q;
डालो(right, cell);
अगर (खाली(left)) { cell = 0; }
वरना { cell = निकालो(left); }
```

A conditional decision tree selects the transition from the current state and
symbol. Use nested `अगर` / `वरना` branches so exactly one transition executes
per iteration; independent `अगर` statements could accidentally execute another
transition after the state changes. Enclose this tree in a `जब तक` loop whose
condition tests that the machine has not halted. A machine that halts terminates
the loop; a machine that runs forever keeps simulating.

## Avoiding a hidden 64-bit assumption

The argument must cover **any** finite machine, not only machines whose alphabet
and state count fit in one integer. Here is a translation without that restriction:

1. For an alphabet of size `m`, choose a fixed positive width `k` with `2^k >= m`.
   Encode symbols as `k` bits, choosing all-zero bits for blank. Represent the
   current symbol with `k` separate Boolean variables.
2. Store each tape cell as `k` consecutive integer bits in a sequence. Push those
   bits in a fixed order; pop them in reverse order into the current Boolean
   variables using comparisons with `1`. Each move expands to exactly `k` pushes
   and `k` pops. These statements are unrolled in the generated Jeetu source;
   no runtime counter or integer length is required. Empty-test occurs before
   popping a whole cell. Stack lengths remain multiples of `k` by construction.
3. Represent machine state with one Boolean variable per state, exactly one
   true. Each branch tests the relevant state Boolean and the `k` current bits.
   Its body assigns the written bits and the next one-hot state, then moves.
4. Use a Boolean `running`, initially true unless the initial state is halting,
   to control the simulation loop. Set it false on entering a halting state.

Each fixed finite machine produces a finite Jeetu program. Symbol writes,
state assignments and bit transfers require only Booleans and the integers
zero and one, so arithmetic overflow cannot interrupt the abstract simulation.
The compiler's physical source-size and nesting limits are implementation
resource limits, just as memory limits are for tape storage.

## Correctness argument

Initialize the sequences with a finite input tape (farther cells pushed first),
the head cell, and the initial state. For the bit encoding, initialize whole
fixed-width cells. Arbitrary finite inputs have finite initializers; a translator
can prepend these to the fixed machine's simulator. A runtime input API is not
needed for this source-encoded input convention.

Assume the representation matches the machine configuration before a step.
The decision tree selects the same state/symbol transition. Writing changes
exactly the current symbol. A right move places that written symbol on the left
stack and obtains the next symbol from the right stack, or blank if empty.
This exactly matches a right-moving tape head. The symmetric reasoning proves
the left move. State updates match the transition table. Thus the representation
invariant holds after one step, and by induction after every finite number of
steps. The loop halts exactly when the simulated machine halts. The represented
tape contains its output, which a machine-specific final loop can print.

Therefore every such Turing-machine computation on every finite input has an
effective Jeetu encoding with the same behavior. Conversely, Jeetu's integer,
Boolean, finite-sequence and control-flow operations are mechanically simulable
by a Turing machine. The abstract language has Turing-machine computational power.

## Executable illustration and practical limits

[The tape example](../examples/tape.jeetu) runs a small two-stack machine that
changes unary `111` to `1111`, then rewinds. It exercises movement in both
directions and the blank-tape convention. It is a concrete illustration, not by
itself the proof of universality or a general machine-table interpreter.

Run it with:

```sh
python3 jeetu.py run examples/tape.jeetu
```

The executable uses bounded host addresses and memory; growth can fail. The
abstract construction never stores an unbounded head position in a 64-bit
integer, but its sequences can grow without bound over time. That distinction
is the basis of the claim.
