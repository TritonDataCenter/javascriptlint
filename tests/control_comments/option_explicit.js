/*jsl:option explicit*/
var g;
function option_explicit(parm) {
    /* legal - j is declared */
    g = j;
    var j;

    var s;

    /* legal - function referencing parameter in parent */
    var fn = function() { return parm; };

    /* legal - function referening variable in parent */
    var fn2 = function() { return s; };

    /* legal - defined below */
    var o = new Child();

    /* legal - function referencing variable in grandparent */
    function Child() {
        function Grandchild() {
            if (parm) {
                return s;
            }
            return null;
        }
    }

    /* legal - catch variable */
    try {
        throw null;
    }
    catch (err) {
        return err;
    }

    /* legal - recursion */
    option_explicit(parm);

    /* legal - this is a property, not a variable */
    this.q = -1;

    /* legal - global */
    g++;

    /* legal - ignore undeclared identifier */
    /*jsl:ignore*/
    g = undefined_var;
    /*jsl:end*/

    /* illegal - undeclared global */
    z--; /*warning:undeclared_identifier*/

    /* illegal - undeclared global */
    y(); /*warning:undeclared_identifier*/

    /* illegal */
    x = 14; /*warning:undeclared_identifier*/

    /* illegal */
    y(); /*warning:undeclared_identifier*/

    // This should be undeclared because this is an expression,
    // not a declaration.
    (function func_expr() { /*warning:misplaced_function*/ /*warning:want_assign_or_call*/
        return 10;
    });
    j = func_expr(); /*warning:undeclared_identifier*/

    return "";
}

// Ensure that we can reference top-level functions.
option_explicit(null);
