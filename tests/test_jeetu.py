import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jeetu import KEYWORDS, Error, compile_source, lex


class JeetuTests(unittest.TestCase):
    def run_program(self, source, output=None, error=None):
        with tempfile.TemporaryDirectory() as directory:
            c = pathlib.Path(directory) / 'test.c'
            binary = pathlib.Path(directory) / 'test'
            c.write_text(compile_source(source))
            command = [os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                       '-Werror', '-pedantic']
            if os.environ.get('SANITIZE'):
                command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
            subprocess.run(command + [str(c), '-o', str(binary)], check=True, capture_output=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=5)
            if error is None:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, output)
                self.assertEqual(result.stderr, '')
            else:
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(error, result.stderr)
                self.assertNotIn('runtime error:', result.stderr)  # UBSan diagnostic
                self.assertNotIn('AddressSanitizer', result.stderr)

    def test_examples(self):
        for path in sorted((ROOT / 'examples').glob('*.jeetu')):
            with self.subTest(name=path.stem):
                self.run_program(path.read_text(), path.with_suffix('.expected').read_text())

    def test_arithmetic_and_scope(self):
        self.run_program('''शुरू {
            मान लो x = 7;
            { मान लो x = x + 1; बोलो x; }
            बोलो x; बोलो 2 + 3 * 4; बोलो (2 + 3) * 4;
            बोलो 20 / 3 / 2; बोलो -7 / 3; बोलो -7 % 3;
            बोलो -9223372036854775808;
            बोलो 9223372036854775807 + 0;
            बोलो -9223372036854775808 * 1;
            बोलो -2 * -3;
            बोलो सच == !झूठ;
        }''', '8\n7\n14\n20\n3\n-2\n-1\n-9223372036854775808\n9223372036854775807\n-9223372036854775808\n6\nsach\n')

    def test_order_and_short_circuit(self):
        self.run_program('''शुरू {
            मान लो s = []; डालो(s, 2); डालो(s, 5);
            बोलो निकालो(s) - निकालो(s);
            बोलो झूठ && (निकालो(s) == 0);
            बोलो सच || (निकालो(s) == 0);
            डालो(s, 9); बोलो आखिरी(s); बोलो खाली(s);
            बोलो निकालो(s); बोलो खाली(s);
        }''', '3\njhooth\nsach\n9\njhooth\n9\nsach\n')

    def test_growth_and_nested_loops(self):
        self.run_program('''शुरू {
            मान लो s = []; मान लो i = 0;
            जब तक (i < 1000) { डालो(s, i); i = i + 1; }
            मान लो sum = 0;
            जब तक (!खाली(s)) { sum = sum + निकालो(s); }
            बोलो sum;
            मान लो a = 0;
            जब तक (a < 3) {
                मान लो b = 0;
                जब तक (b < 2) { b = b + 1; }
                बोलो b; a = a + 1;
            }
        }''', '499500\n2\n2\n2\n')

    def test_lexing_and_strings(self):
        self.run_program('''शुरू {
            मान // comment between keyword words
            लो maanlo = 3;
            बोलो "Namaste, दुनिया!";
            बोलो "quote: \\" and slash: \\\\";
            बोलो "a\\u0000b";
            बोलो maanlo;
        }''', 'Namaste, दुनिया!\nquote: " and slash: \\\na\x00b\n3\n')

    def test_runtime_failures(self):
        cases = [
            ('9223372036854775807 + 1', 'overflow'),
            ('-9223372036854775808 - 1', 'overflow'),
            ('-(-9223372036854775808)', 'overflow'),
            ('9223372036854775807 * 2', 'overflow'),
            ('-9223372036854775808 * -1', 'overflow'),
            ('-9223372036854775808 / -1', 'overflow'),
            ('-9223372036854775808 % -1', 'overflow'),
            ('1 / 0', 'division by zero'), ('1 % 0', 'division by zero')]
        for expr, message in cases:
            with self.subTest(expr=expr):
                self.run_program('शुरू { बोलो ' + expr + '; }', error=message)
        for op in ['निकालो', 'आखिरी']:
            self.run_program('शुरू { मान लो s = []; बोलो ' + op + '(s); }', error='empty sequence')

    def test_rejected_programs(self):
        cases = [
            ('बोलो x;', 'unknown variable'),
            ('मान लो x = x;', 'unknown variable'),
            ('मान लो x = 1; मान लो x = 2;', 'duplicate'),
            ('मान लो x = 1; x = सच;', 'expected int'),
            ('अगर (1) {}', 'expected bool'),
            ('बोलो सच + झूठ;', 'expected int'),
            ('बोलो 9223372036854775808;', 'range'),
            ('मान लो s = []; मान लो t = s;', 'cannot be copied'),
            ('मान लो s = []; s = [];', 'assignment'),
            ('बोलो "a" == "a";', 'equality'),
            ('{ मान लो x = 1; } बोलो x;', 'unknown variable'),
            ('maanlo x = 1;', "expected '='"),
            ('मान लो अगर = 1;', 'variable name'),
            ('बोलो 1', "expected ';'"),
            ('बोलो @;', 'unexpected character'),
            ('बोलो "\\q";', 'invalid string'),
            ('बोलो [];', 'initializer'),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(Error, message):
                    compile_source('शुरू { ' + source + ' }')

    def test_script_distinction(self):
        self.run_program('शुरू { मान लो stack = []; डालो(stack, 7); बोलो आखिरी(stack); बोलो निकालो(stack); बोलो खाली(stack); }', '7\n7\nsach\n')
        self.run_program('शुरू { मान लो shuru = 3; मान लो bolo = 4; बोलो shuru + bolo; बोलो "शुरू shuru"; }', '7\nशुरू shuru\n')
        for keyword in KEYWORDS:
            self.assertEqual(lex(keyword)[0].text, keyword)
        self.assertEqual(lex('बोलो missing;')[1].col, 6)
        with self.assertRaisesRegex(Error, '1:6: unknown variable'):
            compile_source('शुरू{missing = 1;}')
        for source in ['शुरू { मान लो संख्या = 1; }', 'शुरू { बोलो शुरूआत; }',
                       'शुरू { मान लो café = 1; }', 'शुरू { मान लो क़ = 1; }']:
            with self.subTest(source=source), self.assertRaisesRegex(Error, 'ASCII English'):
                compile_source(source)
        for source in ['shuru {}', 'शुरू { maan lo x = 1; }', 'शुरू { मान lo x = 1; }']:
            with self.subTest(source=source), self.assertRaises(Error):
                compile_source(source)
        with self.assertRaisesRegex(Error, 'variable name'):
            compile_source('शुरू { मान लो अगर = 1; }')

    def test_readable_c(self):
        code = compile_source((ROOT / 'examples/factorial.jeetu').read_text())
        main = code.split('int main(void) {', 1)[1].split('/* Source map')[0]
        self.assertIn('int64_t n = 5;', main)
        self.assertIn('int64_t factorial = 1;', main)
        self.assertIn('while (n > 1)', main)
        self.assertIn('factorial = checked_mul(factorial, n);', main)
        self.assertNotIn('jeetu_temp_', main)
        self.assertNotIn('(void)', main)
        self.assertLess(code.index('int main(void)'), code.index('int64_t jeetu_checked_mul(int64_t a, int64_t b, JeetuLocation location) {'))
        self.assertIn('text_print(TEXT("Hello!"), true);', compile_source('शुरू { बोलो "Hello!"; }'))
        self.run_program('शुरू { बोलो "??/"; }', '??/\n')

    def test_generated_name_collisions_and_unused_variables(self):
        self.run_program('शुरू {\n            मान लो int = 1; मान लो printf = 2; मान लो INT64_MAX = 3;\n            मान लो checked_mul = 4; मान लो jeetu_temp_1 = 5;\n            मान लो _private = 6; मान लो value = 7;\n            { मान लो value = value + 1; बोलो value; }\n            मान लो value_2 = 9;\n            बोलो int + printf + INT64_MAX + checked_mul + jeetu_temp_1 + _private;\n            बोलो value; बोलो value_2;\n            मान लो unused = 1; unused = 2;\n            मान लो empty = [];\n        }', '8\n21\n7\n9\n')

    def test_deferred_expression_order(self):
        self.run_program('शुरू {\n            मान लो s = []; डालो(s, 2); डालो(s, 5);\n            बोलो आखिरी(s) + निकालो(s);\n            बोलो खाली(s) == (निकालो(s) == 2);\n            बोलो झूठ && (निकालो(s) + निकालो(s) == 0);\n            बोलो सच || (निकालो(s) + निकालो(s) == 0);\n            डालो(s, 1); डालो(s, 2); डालो(s, 3); डालो(s, 4);\n            बोलो (निकालो(s) + निकालो(s)) * (निकालो(s) + निकालो(s));\n            डालो(s, 1); डालो(s, 2); डालो(s, 3); डालो(s, 4);\n            जब तक (!खाली(s) && (निकालो(s) + निकालो(s) > 0)) {\n                बोलो "pair";\n            }\n        }', '10\njhooth\njhooth\nsach\n21\npair\npair\n')
        self.run_program('शुरू { बोलो (1 / 0) + (9223372036854775807 + 1); }', error='division by zero')
        self.run_program('शुरू { मान लो s = []; बोलो निकालो(s) + (1 / 0); }', error='empty sequence')
        self.run_program('शुरू { बोलो 1 / 0; }', error='at 1:8:')
        self.run_program('शुरू { मान लो x = 1; बोलो x == x; बोलो x < x; }', 'sach\njhooth\n')

    def test_functions_and_borrowed_sequences(self):
        self.run_program('कार्य append(values: सूची, value: पूर्णांक): पूर्णांक {\n            डालो(values, value); लौटाओ लंबाई(values);\n        }\n        कार्य pick(flag: बूलियन, n: पूर्णांक): पूर्णांक {\n            मान लो local = [7, 9];\n            अगर (flag) { लौटाओ निकालो(local); }\n            लौटाओ n;\n        }\n        कार्य combine(a: पूर्णांक, b: पूर्णांक): पूर्णांक { लौटाओ a * 10 + b; }\n        शुरू {\n            मान लो s = [];\n            बोलो combine(append(s, 4), append(s, 8));\n            बोलो s[0]; बोलो s[1];\n            बोलो pick(सच, 3); बोलो pick(झूठ, 3);\n        }', '12\n4\n8\n9\n3\n')

    def test_unreachable_declarations_and_aliases(self):
        self.run_program('कार्य f(): पूर्णांक { लौटाओ 1; मान लो unused = 2; मान लो unusedStack = []; } शुरू { बोलो f(); }', '1\n')
        self.run_program('कार्य f(a: सूची, b: सूची): पूर्णांक { डालो(a, 5); लौटाओ b[0]; } शुरू { मान लो s = []; बोलो f(s, s); बोलो लंबाई(s); }', '5\n1\n')

    def test_break_continue_cleanup(self):
        self.run_program('शुरू {\n            मान लो outer = [8]; मान लो i = 0; मान लो sum = 0;\n            जब तक (i < 5) {\n                मान लो local = [i]; i = i + 1;\n                अगर (i == 2) { जारी; }\n                मान लो j = 0;\n                जब तक (j < 3) {\n                    मान लो inner = [j]; j = j + 1;\n                    अगर (j == 2) { रुको; }\n                    sum = sum + inner[0] + 1;\n                }\n                अगर (i == 4) { रुको; }\n                sum = sum + local[0];\n            }\n            बोलो sum; बोलो outer[0];\n        }', '5\n8\n')

    def test_text_and_indexing(self):
        self.run_program('कार्य character(text: पाठ, i: पूर्णांक): पाठ { लौटाओ text[i]; }\n        शुरू {\n            मान लो word = "A🙂é"; मान लो copy = word;\n            word = "changed";\n            बोलो लंबाई(copy); बोलो character(copy, 1);\n            मान लो empty = []; बोलो लंबाई(empty);\n            लिखो "a\\u0000b"; बोलो "";\n        }', '3\n🙂\n0\na\x00b\n')
        for program, message in [
            ('शुरू { मान लो a = [1]; बोलो a[-1]; }', 'sequence index'),
            ('शुरू { मान लो a = []; बोलो a[0]; }', 'sequence index'),
            ('शुरू { बोलो ""[0]; }', 'text index'),
            ('शुरू { बोलो "🙂"[1]; }', 'text index'),
            ('शुरू { बोलो "abc"[-1]; }', 'text index'),
        ]:
            with self.subTest(program=program):
                self.run_program(program, error=message)

    def test_rejected_functions_and_transfers(self):
        cases = [
            ('शुरू { रुको; }', 'inside a loop'),
            ('शुरू { जारी; }', 'inside a loop'),
            ('शुरू { लौटाओ 1; }', 'inside a function'),
            ('कार्य f(): पूर्णांक { रुको; लौटाओ 1; } शुरू {}', 'inside a loop'),
            ('कार्य f(): पूर्णांक {} शुरू {}', 'every path'),
            ('कार्य f(n: पूर्णांक): पूर्णांक { अगर (n > 0) { लौटाओ n; } } शुरू {}', 'every path'),
            ('कार्य f(): पूर्णांक { लौटाओ सच; } शुरू {}', 'expected int'),
            ('कार्य f(x: पूर्णांक, x: पूर्णांक): पूर्णांक { लौटाओ x; } शुरू {}', 'duplicate parameter'),
            ('कार्य f(): पूर्णांक { लौटाओ 1; } कार्य f(): पूर्णांक { लौटाओ 2; } शुरू {}', 'duplicate function'),
            ('शुरू { बोलो missing(1); }', 'unknown function'),
            ('कार्य f(x: पूर्णांक): पूर्णांक { लौटाओ x; } शुरू { बोलो f(); }', 'expects 1'),
            ('कार्य f(x: पूर्णांक): पूर्णांक { लौटाओ x; } शुरू { बोलो f(सच); }', 'expected int'),
            ('कार्य f(): पूर्णांक { लौटाओ outer; } शुरू { मान लो outer = 1; }', 'unknown variable'),
            ('कार्य f(): सूची { मान लो s = []; लौटाओ s; } शुरू {}', 'cannot return owned'),
            ('शुरू { मान लो s = [1, सच]; }', 'expected int'),
            ('शुरू { बोलो 5[0]; }', 'indexing requires'),
        ]
        for program, message in cases:
            with self.subTest(program=program), self.assertRaisesRegex(Error, message):
                compile_source(program)

    def test_recursive_error_locations(self):
        self.run_program('कार्य recurse(n: पूर्णांक): पूर्णांक {\n    अगर (n == 0) { लौटाओ 1; }\n    लौटाओ recurse(n - 1) / 0;\n}\nशुरू { बोलो recurse(2); }\n', error='at 3:5:')

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            c = pathlib.Path(directory) / 'factorial.c'
            exe = pathlib.Path(directory) / 'factorial'
            base = [sys.executable, str(ROOT / 'jeetu.py')]
            source = str(ROOT / 'examples/factorial.jeetu')
            for args in [['check', source], ['emit-c', source, '-o', str(c)],
                         ['build', source, '-o', str(exe)]]:
                result = subprocess.run(base + args, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('int main(void)', c.read_text())
            retained = pathlib.Path(str(exe) + '.c')
            self.assertEqual(retained.read_text(), c.read_text())
            standalone = pathlib.Path(directory) / 'standalone'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                            str(retained), '-I', str(ROOT / 'runtime'), str(ROOT / 'runtime/jeetu_runtime.c'), '-o', str(standalone)], check=True)
            self.assertEqual(subprocess.check_output([str(standalone)], text=True), '120\n')
            self.assertEqual(subprocess.check_output([str(exe)], text=True), '120\n')
            self.assertEqual(subprocess.check_output(base + ['run', source], text=True), '120\n')
            result = subprocess.run(base + ['emit-c', source, '--standalone', '-o', str(c)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', str(c), '-o', str(standalone)], check=True)
            self.assertEqual(subprocess.check_output([str(standalone)], text=True), '120\n')


if __name__ == '__main__':
    unittest.main()
