/*jsl:option explicit*/
function redeclared_var() {
    var duplicate;
    var duplicate; /*warning:redeclared_var*/

    function myFunction() {
        return;
    }
    var myFunction; /*warning:redeclared_var*/

    // myFunction isn't a redeclaration, since function names in function
    // expressions don't affect the outer scope -- they do however introduce
    // it into the declared function's scope
    var tmp = function myFunction(){}; /*warning:identifier_hides_another*/
    /*jsl:unused tmp*/
}
