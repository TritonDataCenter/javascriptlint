/*jsl:option explicit*/
function equal_as_assign() {
    var a, b;
    while (a = b) { /*warning:equal_as_assign*/
        a++;
    }
    while (a -= b) {
        a--;
    }

    var c;
    a = b = c;

    var x, y, z;
    var w = x = y = z;
}
