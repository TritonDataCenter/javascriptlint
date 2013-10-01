/*conf:+function_name_mismatch*/
function function_name_mismatch() {
    var f = function bogus() { /*warning:function_name_mismatch*/
    };
    var g = function g() {
    };

    f = new function bogus() {
    };
    f = new function() {
    };

    f = (function() {
        return 10;
    })();

    var o = {
        f: function bogus() { /*warning:function_name_mismatch*/
            return null;
        }
    };
    o.a.b = {
        f: function bogus() { /*warning:function_name_mismatch*/
            return null;
        }
    };
    o.a.b = o.a.b || function bogus() { return 10; }; /*warning:function_name_mismatch*/

    function closure(a) {
        return function() { return a; };
    }

    function x() {
    }
}

