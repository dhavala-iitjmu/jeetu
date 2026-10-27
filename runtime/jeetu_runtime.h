#ifndef JEETU_RUNTIME_H
#define JEETU_RUNTIME_H

#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int64_t *data;
    size_t len, cap;
} IntStack;

/* Immutable UTF-8 views backed by program-lifetime string literals. */
typedef struct { const char *data; size_t bytes; } Text;
#define TEXT(literal) ((Text){(literal), sizeof(literal) - 1})

typedef struct { int line, column; } JeetuLocation;
/* Defined by the generated program; maps C lines back to Jeetu statements. */
JeetuLocation jeetu_source_location(int generated_line);

int64_t jeetu_checked_add(int64_t a, int64_t b, JeetuLocation location);
int64_t jeetu_checked_sub(int64_t a, int64_t b, JeetuLocation location);
int64_t jeetu_checked_mul(int64_t a, int64_t b, JeetuLocation location);
int64_t jeetu_checked_div(int64_t a, int64_t b, JeetuLocation location);
int64_t jeetu_checked_mod(int64_t a, int64_t b, JeetuLocation location);
void jeetu_stack_push(IntStack *stack, int64_t value, JeetuLocation location);
int64_t jeetu_stack_top(IntStack *stack, JeetuLocation location);
int64_t jeetu_stack_pop(IntStack *stack, JeetuLocation location);

/* Each argument is evaluated exactly once. Location lookup is side-effect free. */
#define checked_add(a, b) jeetu_checked_add((a), (b), jeetu_source_location(__LINE__))
#define checked_sub(a, b) jeetu_checked_sub((a), (b), jeetu_source_location(__LINE__))
#define checked_mul(a, b) jeetu_checked_mul((a), (b), jeetu_source_location(__LINE__))
#define checked_div(a, b) jeetu_checked_div((a), (b), jeetu_source_location(__LINE__))
#define checked_mod(a, b) jeetu_checked_mod((a), (b), jeetu_source_location(__LINE__))
#define stack_push(a, b) jeetu_stack_push((a), (b), jeetu_source_location(__LINE__))
#define stack_top(a) jeetu_stack_top((a), jeetu_source_location(__LINE__))
#define stack_pop(a) jeetu_stack_pop((a), jeetu_source_location(__LINE__))

void text_print(Text text, bool newline);
int64_t jeetu_stack_length(IntStack *stack, JeetuLocation location);
int64_t jeetu_stack_get(IntStack *stack, int64_t index, JeetuLocation location);
int64_t jeetu_text_length(Text text, JeetuLocation location);
Text jeetu_text_at(Text text, int64_t index, JeetuLocation location);
#define stack_length(a) jeetu_stack_length((a), jeetu_source_location(__LINE__))
#define stack_get(a, b) jeetu_stack_get((a), (b), jeetu_source_location(__LINE__))
#define text_length(a) jeetu_text_length((a), jeetu_source_location(__LINE__))
#define text_at(a, b) jeetu_text_at((a), (b), jeetu_source_location(__LINE__))

#endif
