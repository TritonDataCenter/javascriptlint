/*jsl:option explicit*/
function useless_comparison() {
    var i, j, o;

    /* Test expressions */
    if (i+2 < i+2) { /*warning:useless_comparison*/
        return;
    }
    if (j != j) { /*warning:useless_comparison*/
        i++;
    }
    if ((14 * i) / (j - 2) >= (14 * i) / (j - 2)) { /*warning:useless_comparison*/
        return;
    }

    /* Test properties */
    if (o.left == o.left) { /*warning:useless_comparison*/
        return;
    }
    if (o.left == o['left']) { /*warning:useless_comparison*/
        return;
    }
    if (o['left'] == o['left']) { /*warning:useless_comparison*/
        return;
    }
    if (o[i] == o[i]) { /*warning:useless_comparison*/
        return;
    }

    if (o.left == o.right) {
        return;
    }
    if (o['left'] == o.right) {
        return;
    }
    if (o['left'] == o['right']) {
        return;
    }
    if (o[i] == o[j]) {
        return;
    }
    if (o[i] == o.right) {
        return;
    }

    /* Complex expressions not caught because of slight differences */
    if ((14 * i) / (j - 2) == (i * 14) / (j - 2)) {
        return;
    }

    /* allowed since function may have side affects */
    if (useless_comparison() == useless_comparison()) {
        return;
    }
    
    // Test multiple comparisons.
    if (i == i == 3) /*warning:useless_comparison*/
        return;
    if (i == 3 == i) /*warning:useless_comparison*/
        return;
    if (i == 3 == j == 3) /*warning:useless_comparison*/
        return;

    // Test bases
    if (010 == 8) /*warning:useless_comparison*/ /*warning:octal_number*/
        return;
    if (0xA == 10) /*warning:useless_comparison*/
        return;
}
