/*jsl:option explicit*/
function bad_backref() {
    /* illegal - one 1 backreference */
    return /(.)\2/; /* TODO: Implement regex warnings. */
}
