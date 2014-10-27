function unreachable_loop_condition(skip) {
    /* continue will run the condition.
     */
    for (var i = 0; i < 10; i++) {
        if (skip)
            continue;
        break;
    }

    for (i = 0; i < 10; i++) { /*warning:unreachable_code*/
        if (skip)
            return;
        break;
    }


    /* test with do..while
     */
    i = 0;
    do {
        i += 1;
        if (skip)
            continue;
        break;
    } while(i < 10);

    i = 0;
    do {
        i += 1;
        if (skip)
            return;
        break;
    } while(i < 10); /*warning:unreachable_code*/

}

