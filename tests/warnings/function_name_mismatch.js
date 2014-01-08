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

    function Class() {
        this.getStr = function getSt() { /*warning:function_name_mismatch*/
            return this.str;
        };
        this.setStr = function setStr(s) {
            this.str = s;
        };
    }
    Class.prototype.get = function gt() { /*warning:function_name_mismatch*/
        return this.value;
    };
    Class.prototype.set = function set(value) {
        this.value = value;
    };
}

