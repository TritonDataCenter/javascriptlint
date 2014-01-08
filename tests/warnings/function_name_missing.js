/*conf:+function_name_missing*/
function function_name_missing() {
    var f = function() { /*warning:function_name_missing*/
    };
    f = new function() {
    };
    f = (function() {
        return 10;
    })();

    var o = {
        f: function() { /*warning:function_name_missing*/
            return null;
        }
    };
    o.a.b = {
        f: function() { /*warning:function_name_missing*/
            return null;
        }
    };
    o.a.b = o.a.b || function() { return 10; }; /*warning:function_name_missing*/

    function closure(a) {
        return function() { return a; };
    }

    function x() {
    }

    function Class() {
        this.getStr = function () { /*warning:function_name_missing*/
            return this.str;
        };
        this.setStr = function setStr(s) {
            this.str = s;
        };
    }
    Class.prototype.get = function () { /*warning:function_name_missing*/
        return this.value;
    };
    Class.prototype.set = function set(value) {
        this.value = value;
    };
}

