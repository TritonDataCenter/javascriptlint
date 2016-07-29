/*conf:-want_assign_or_call*/
function misplaced_functions() {
    var f = function() {
    };
    f = new function() {
    };
    f = (function() {
        return 10;
    })();

    var o = {
        f: function() {
            return null;
        }
    };
    o.a.b = {
        f: function() {
            return null;
        }
    };
    o.a.b = o.a.b || function() { return 10; };
    o.a.b = o.a.c || function() { return 10; }; /*TODO*/

    function closure(a) {
        return function() { return a; };
    }

    function x() {
    }

    function() {}; /*warning:misplaced_function*/
}

