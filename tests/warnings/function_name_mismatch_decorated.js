/*conf:+function_name_mismatch*/
/*conf:+decorate_function_name_warning*/
function function_name_mismatch_decorated() {
    var f = function bogus() { /*warning:function_name_mismatch*/
    };
    var g = function g() { /*warning:function_name_mismatch*/
    };
    var h = function __h() {
    };

    f = new function bogus() {
    };
    f = new function() {
    };

    f = (function() {
        return 10;
    })();

    function Class() {
    }
    Class.prototype.get = function gt() { /*warning:function_name_mismatch*/
        return this.value;
    };
    Class.prototype.set = function set(value) { /*warning:function_name_mismatch*/
        this.value = value;
    };
    Class.prototype.inc = function __inc(value) {
        this.value++;
    };
}

