function foo() {
    foo();
}

foo(function bar() {
    foo(bar, 1000);
}, 1000);
