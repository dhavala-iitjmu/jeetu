#include "jeetu_runtime.h"

static void runtime_error(JeetuLocation location, const char *message) {
    fprintf(stderr, "Jeetu runtime error at %d:%d: %s\n", location.line, location.column, message);
    exit(1);
}
int64_t jeetu_checked_add(int64_t a, int64_t b, JeetuLocation location) {
    if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b))
        runtime_error(location, "integer overflow");
    return a + b;
}
int64_t jeetu_checked_sub(int64_t a, int64_t b, JeetuLocation location) {
    if ((b > 0 && a < INT64_MIN + b) || (b < 0 && a > INT64_MAX + b))
        runtime_error(location, "integer overflow");
    return a - b;
}
int64_t jeetu_checked_mul(int64_t a, int64_t b, JeetuLocation location) {
    if ((a > 0 && b > 0 && a > INT64_MAX / b) ||
        (a > 0 && b < 0 && b < INT64_MIN / a) ||
        (a < 0 && b > 0 && a < INT64_MIN / b) ||
        (a < 0 && b < 0 && a < INT64_MAX / b))
        runtime_error(location, "integer overflow");
    return a * b;
}
static void check_divisor(int64_t a, int64_t b, JeetuLocation location) {
    if (b == 0) runtime_error(location, "division by zero");
    if (a == INT64_MIN && b == -1) runtime_error(location, "integer overflow");
}
int64_t jeetu_checked_div(int64_t a, int64_t b, JeetuLocation location) {
    check_divisor(a, b, location);
    return a / b;
}
int64_t jeetu_checked_mod(int64_t a, int64_t b, JeetuLocation location) {
    check_divisor(a, b, location);
    return a % b;
}
void jeetu_stack_push(IntStack *stack, int64_t value, JeetuLocation location) {
    if (stack->len == stack->cap) {
        size_t limit = SIZE_MAX / sizeof(int64_t);
        if (stack->cap >= limit) runtime_error(location, "sequence capacity exhausted");
        size_t next = stack->cap == 0 ? (limit < 8 ? limit : 8) :
            (stack->cap > limit / 2 ? limit : stack->cap * 2);
        int64_t *data = realloc(stack->data, next * sizeof(int64_t));
        if (!data) runtime_error(location, "sequence allocation failed");
        stack->data = data;
        stack->cap = next;
    }
    stack->data[stack->len++] = value;
}
int64_t jeetu_stack_top(IntStack *stack, JeetuLocation location) {
    if (stack->len == 0) runtime_error(location, "empty sequence");
    return stack->data[stack->len - 1];
}
int64_t jeetu_stack_pop(IntStack *stack, JeetuLocation location) {
    int64_t value = jeetu_stack_top(stack, location);
    --stack->len;
    return value;
}

int64_t jeetu_stack_length(IntStack *stack, JeetuLocation location) {
#if SIZE_MAX > INT64_MAX
    if (stack->len > INT64_MAX) runtime_error(location, "sequence length exceeds integer range");
#else
    (void)location;
#endif
    return (int64_t)stack->len;
}

int64_t jeetu_stack_get(IntStack *stack, int64_t index, JeetuLocation location) {
    if (index < 0 || (uint64_t)index >= stack->len)
        runtime_error(location, "sequence index out of bounds");
    return stack->data[(size_t)index];
}

void text_print(Text text, bool newline) {
    fwrite(text.data, 1, text.bytes, stdout);
    if (newline) putchar('\n');
}

int64_t jeetu_text_length(Text text, JeetuLocation location) {
    int64_t count = 0;
    for (size_t i = 0; i < text.bytes; ++i) {
        if (((unsigned char)text.data[i] & 0xc0) != 0x80) {
            if (count == INT64_MAX) runtime_error(location, "text length exceeds integer range");
            ++count;
        }
    }
    return count;
}

Text jeetu_text_at(Text text, int64_t index, JeetuLocation location) {
    if (index < 0) runtime_error(location, "text index out of bounds");
    int64_t count = 0;
    for (size_t start = 0; start < text.bytes;) {
        size_t end = start + 1;
        while (end < text.bytes && ((unsigned char)text.data[end] & 0xc0) == 0x80) ++end;
        if (count == index) return (Text){text.data + start, end - start};
        if (count == INT64_MAX) break;
        ++count;
        start = end;
    }
    runtime_error(location, "text index out of bounds");
    return (Text){NULL, 0};
}
