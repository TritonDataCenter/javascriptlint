
/* Should be possible to have /= for start of regex */
var a = /=/g;

/* But doing so shouldn't affect using /= assignment */
var b = 6;
b /= 4;
var d = (b /=5);
