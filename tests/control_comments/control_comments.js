/*jsl:option explicit*/
function control_comments() {
    /* "legal" - can do anything */
    /*jsl:ignore*/
    var a;
    if (a);
       var b = a = b+++a;
       var a = b;
    /*jsl:end*/
    /*@ignore@*/
    var a;
    if (a);
       var b = a = b+++a;
       var a = b;
    /*@end@*/

    /* legal - case doesn't matter */
    /*Jsl:IGNORE*/
    asdf = asdf;
    /*JSL:End*/

    /* illegal - not ending anything */
    /*jsl:end*/ /*warning:mismatch_ctrl_comments*/

    /* illegal - can't start twice */
    /*jsl:ignore*/
    /*jsl:ignore*/ /*warning:mismatch_ctrl_comments*/
    /*jsl:end*/

    /* illegal - don't forget to end */
    /*jsl:ignore*/ /*warning:mismatch_ctrl_comments*/

    // The following are illegal. Make sure jsl doesn't choke.
    /*jsl:*/ /*warning:jsl_cc_not_understood*/
    if (a) {
       /*jsl:pass */
    }
    else if (b) {
       /* jsl:pass */ //allow spaces on both sides
    }
    /*jsl:ignoreal*/ /*warning:jsl_cc_not_understood*/
    /*jsl:declarebogus*/ /*warning:jsl_cc_not_understood*/
    /*jsl:declare bogus */
}

