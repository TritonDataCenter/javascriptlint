/*jsl:option explicit*/
function for_in_missing_identifier(o) {
	var prop;
	for (prop in o)
		o[prop]++;
	
	for (var prop2 in o)
		o[prop2]++;

	for (!prop in o) /*warning:for_in_missing_identifier*/
		o[prop]++;
}
