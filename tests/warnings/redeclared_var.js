/*jsl:option explicit*/
function redeclared_var() {
    var duplicate;
    var duplicate; /*warning:redeclared_var*/

    function myFunction() {
        return;
    }
    var myFunction; /*warning:redeclared_var*/

    // myFunction isn't a redeclaration, since function names in function
    // expressions don't matter.
    var tmp = function myFunction(){};
    /*jsl:unused tmp*/
}
