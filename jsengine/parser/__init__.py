# vim: sw=4 ts=4 et
import unittest

from jsengine.tokenizer import tok
from jsengine import tokenizer

from jsengine import JSSyntaxError
from _constants_kind import kind
from _constants_op import op

from jsengine.structs import *

_VERSIONS = [
    "default",
    "1.0",
    "1.1",
    "1.2",
    "1.3",
    "1.4",
    "1.5",
    "1.6",
    "1.7",
]

def _auto_semicolon(t, kind_, op_, startpos, endpos, atom, kids):
    nosemi = False
    if t.peek_sameline().tok not in (tok.EOF, tok.EOL, tok.RBRACE):
        x = t.advance()
        if x.tok != tok.SEMI:
            raise JSSyntaxError(x.startpos, 'semi_before_stmnt')
        endpos = x.endpos
    else:
        nosemi = True
    return ParseNode(kind_, op_, startpos, endpos, atom, kids, nosemi)

def _function_arglist(t):
    fn_args = []
    if t.peek().tok != tok.RPAREN:
        while True:
            x = t.expect(tok.NAME)
            fn_args.append(ParseNode(kind.NAME, op.ARGNAME,
                                     x.startpos,
                                     x.endpos, x.atom, []))
            if t.peek().tok == tok.COMMA:
                t.advance()
            else:
                break
    return fn_args

def _primary_expression(t):
    x = t.next_withregexp()
    if x.tok == tok.THIS:
        return ParseNode(kind.PRIMARY, op.THIS, x.startpos, x.endpos, None, [])
    elif x.tok == tok.NAME:
        return ParseNode(kind.NAME, op.NAME, x.startpos, x.endpos, x.atom, [None])
    elif x.tok == tok.NULL:
        return ParseNode(kind.PRIMARY, op.NULL, x.startpos, x.endpos, None, [])
    elif x.tok == tok.TRUE:
        return ParseNode(kind.PRIMARY, op.TRUE, x.startpos, x.endpos, None, [])
    elif x.tok == tok.FALSE:
        return ParseNode(kind.PRIMARY, op.FALSE, x.startpos, x.endpos, None, [])
    elif x.tok == tok.STRING:
        return ParseNode(kind.STRING, op.STRING, x.startpos, x.endpos, x.atom, [])
    elif x.tok == tok.REGEXP:
        return ParseNode(kind.OBJECT, op.REGEXP, x.startpos, x.endpos, None, [])
    elif x.tok == tok.NUMBER:
        return ParseNode(kind.NUMBER, None, x.startpos, x.endpos, x.atom, [])
    elif x.tok == tok.LBRACKET:
        startpos = x.startpos
        items = []
        end_comma = None
        if t.peek().tok != tok.RBRACKET:
            while True:
                # Conditionally add a value. If it isn't followed by a comma,
                # quit in order to force an RBRACKET.
                if t.peek().tok == tok.COMMA:
                    items.append(None)
                else:
                    items.append(_assignment_expression(t, True))
                    if not t.peek().tok == tok.COMMA:
                        break

                # Expect a comma and use it if the value was missing.
                x = t.expect(tok.COMMA)
                comma = ParseNode(kind.COMMA, None,
                                  x.startpos, x.endpos, None, [])
                items[-1] = items[-1] or comma

                # Check for the end.
                if t.peek().tok == tok.RBRACKET:
                    end_comma = comma
                    break
        endpos = t.expect(tok.RBRACKET).endpos
        return ParseNode(kind.RB, None, startpos, endpos, None, items,
                         end_comma=end_comma)
    elif x.tok == tok.LBRACE:
        startpos = x.startpos
        kids = []
        # TODO: get/set
        end_comma = None
        while True:
            x = t.peek()
            if x.tok == tok.RBRACE:
                break
            elif x.tok == tok.STRING:
                t.expect(tok.STRING)
                key = ParseNode(kind.STRING, None, x.startpos,
                                x.endpos, x.atom, [])
            elif x.tok == tok.NUMBER:
                t.expect(tok.NUMBER)
                key = ParseNode(kind.NUMBER, None, x.startpos,
                                x.endpos, x.atom, [])
            else:
                x = t.expect_identifiername()
                key = ParseNode(kind.NAME, None, x.startpos, x.endpos,
                                x.atom, [])
            t.expect(tok.COLON)
            value = _assignment_expression(t, True)
            kids.append(ParseNode(kind.COLON, None, key.startpos,
                                  value.endpos, None, [key, value]))
            if t.peek().tok == tok.COMMA:
                x = t.advance()
                end_comma = ParseNode(kind.COMMA, None,
                                      x.startpos, x.endpos, None, [])
            else:
                end_comma = None
                break
        endpos = t.expect(tok.RBRACE).endpos
        return ParseNode(kind.RC, None, startpos, endpos, None, kids,
                         end_comma=end_comma)
    elif x.tok == tok.LPAREN:
        startpos = x.startpos
        kid = _expression(t, True)
        endpos = t.expect(tok.RPAREN).endpos
        return ParseNode(kind.RP, None, startpos, endpos, None, [kid])
    else:
        raise JSSyntaxError(x.startpos, 'syntax_error')

def _function_declaration(t, named_opcode):
    node = _function_expression(t, named_opcode)

    # Convert anonymous functions in expressions.
    if node.opcode == op.ANONFUNOBJ:
        node = _auto_semicolon(t, kind.SEMI, None, node.startpos, node.endpos,
                               None, [node])
    return node


def _function_expression(t, named_opcode):
    startpos = t.expect(tok.FUNCTION).startpos
    if t.peek().tok == tok.NAME:
        fn_name = t.expect(tok.NAME).atom
        opcode = named_opcode
    else:
        fn_name = None
        opcode = op.ANONFUNOBJ
    t.expect(tok.LPAREN)
    fn_args = _function_arglist(t)
    t.expect(tok.RPAREN)
    fn_body_startpos = t.expect(tok.LBRACE).startpos
    kids = _sourceelements(t, tok.RBRACE)
    fn_body_endpos = t.expect(tok.RBRACE).endpos
    fn_body = ParseNode(kind.LC, None, fn_body_startpos,
                        fn_body_endpos, None, kids)
    return ParseNode(kind.FUNCTION, opcode, startpos, fn_body.endpos,
                     fn_name, [fn_body], fn_args=fn_args)

def _argument_list(t):
    args = []
    if t.peek().tok != tok.RPAREN:
        while True:
            args.append(_assignment_expression(t, True))
            if t.peek().tok == tok.COMMA:
                t.advance()
            else:
                break
    return args

def _new_expression(t):
    startpos = t.expect(tok.NEW).startpos
    expr = _member_expression(t)
    # If no (), this is a variant of the NewExpression
    if t.peek().tok == tok.LPAREN:
        t.expect(tok.LPAREN)
        args = _argument_list(t)
        endpos = t.expect(tok.RPAREN).endpos
    else:
        args = []
        endpos = expr.endpos
    return ParseNode(kind.NEW, op.NEW, startpos, endpos,
                     None, [expr] + args)

def _member_expression(t, _recurse=True):
    x = t.peek()
    if x.tok == tok.NEW:
        kid = _new_expression(t)
    elif x.tok == tok.FUNCTION:
        kid = _function_expression(t, op.NAMEDFUNOBJ)
    else:
        kid = _primary_expression(t)

    while True:
        if t.peek().tok == tok.LBRACKET:
            t.advance()
            expr = _expression(t, True)
            endpos = t.expect(tok.RBRACKET).endpos
            kid = ParseNode(kind.LB, op.GETELEM, kid.startpos, endpos,
                            None, [kid, expr])
        elif t.peek().tok == tok.DOT:
            t.advance()
            expr = t.expect_identifiername()
            kid = ParseNode(kind.DOT, op.GETPROP, kid.startpos, expr.endpos,
                            expr.atom, [kid])
        else:
            return kid

def _call_expression(t):
    expr = _member_expression(t)
    if t.peek().tok != tok.LPAREN:
        return expr

    while True:
        x = t.peek()
        if x.tok == tok.LPAREN:
            t.expect(tok.LPAREN)
            args = _argument_list(t)
            endpos = t.expect(tok.RPAREN).endpos
            expr = ParseNode(kind.LP, op.CALL, expr.startpos,
                             endpos, None, [expr] + args)
        elif x.tok == tok.LBRACKET:
            t.expect(tok.LBRACKET)
            lookup = _expression(t, True)
            endpos = t.expect(tok.RBRACKET).endpos
            expr = ParseNode(kind.LB, op.GETELEM,
                             expr.startpos, endpos,
                             None, [expr, lookup])
        elif x.tok == tok.DOT:
            t.expect(tok.DOT)
            lookup = t.expect_identifiername()
            expr = ParseNode(kind.DOT, op.GETPROP,
                             expr.startpos, lookup.endpos,
                             lookup.atom, [expr])
        else:
            return expr

def _lefthandside_expression(t):
    kid = _call_expression(t)
    kid._lefthandside = True
    return kid

def _postfix_expression(t):
    kid = _lefthandside_expression(t)
    if t.peek_sameline().tok == tok.INC:
        endpos = t.expect(tok.INC).endpos
        if kid.kind == kind.DOT and kid.opcode == op.GETPROP:
            opcode = op.PROPINC
        else:
            opcode = op.NAMEINC
        return ParseNode(kind.INC, opcode,
                         kid.startpos, endpos, None, [kid])
    elif t.peek_sameline().tok == tok.DEC:
        endpos = t.expect(tok.DEC).endpos
        return ParseNode(kind.DEC, op.NAMEDEC,
                         kid.startpos, endpos, None, [kid])
    else:
        return kid

_UNARY = {
    tok.DELETE: (kind.DELETE, None),
    tok.VOID: (kind.UNARYOP, op.VOID),
    tok.TYPEOF: (kind.UNARYOP, op.TYPEOF),
    tok.INC: (kind.INC, op.INCNAME),
    tok.DEC: (kind.DEC, op.DECNAME),
    tok.ADD: (kind.UNARYOP, op.POS),
    tok.SUB: (kind.UNARYOP, op.NEG),
    tok.BIT_NOT: (kind.UNARYOP, op.BITNOT),
    tok.LOGICAL_NOT: (kind.UNARYOP, op.NOT),
}
def _unary_expression(t):
    x = t.peek()
    if x.tok in _UNARY:
        kind_, op_ = _UNARY[x.tok]
        startpos = t.advance().startpos
        kid = _unary_expression(t)
        return ParseNode(kind_, op_, startpos, kid.endpos, None, [kid])
    else:
        return _postfix_expression(t)

def _binary_expression(t, dict_, child_expr_callback):
    expr = child_expr_callback(t)
    while True:
        x = t.peek()
        try:
            kind_, op_ = dict_[x.tok]
        except KeyError:
            return expr

        kids = [expr]
        while t.peek().tok == x.tok:
            t.advance()
            kids.append(child_expr_callback(t))
        expr = ParseNode(kind_, op_,
                         kids[0].startpos, kids[1].endpos,
                         None, kids)

_MULTIPLICATIVE = {
    tok.MUL: (kind.STAR, op.MUL),
    tok.DIV: (kind.DIVOP, op.DIV),
    tok.MOD: (kind.DIVOP, op.MOD),
}
def _multiplicative_expression(t):
    return _binary_expression(t, _MULTIPLICATIVE, _unary_expression)

_ADDITIVE = {
    tok.ADD: (kind.PLUS, op.ADD),
    tok.SUB: (kind.MINUS, op.SUB),
}
def _additive_expression(t):
    return _binary_expression(t, _ADDITIVE,
                              _multiplicative_expression)

_SHIFT = {
    tok.LSHIFT: (kind.SHOP, op.LSH),
    tok.RSHIFT: (kind.SHOP, op.RSH),
    tok.URSHIFT: (kind.SHOP, op.URSH),
}
def _shift_expression(t):
    return _binary_expression(t, _SHIFT,
                              _additive_expression)

_RELATIONAL_NOIN = {
    tok.LT: (kind.RELOP, op.LT),
    tok.GT: (kind.RELOP, op.GT),
    tok.LE: (kind.RELOP, op.LE),
    tok.GE: (kind.RELOP, op.GE),
    tok.INSTANCEOF: (kind.INSTANCEOF, op.INSTANCEOF),
}
_RELATIONAL_IN = dict(_RELATIONAL_NOIN)
_RELATIONAL_IN.update({
    tok.IN: (kind.IN, op.IN),
})
def _relational_expression(t, allowin):
    return _binary_expression(t, _RELATIONAL_IN if allowin else _RELATIONAL_NOIN,
                              _shift_expression)

_EQUALITY = {
    tok.EQ: (kind.EQOP, op.EQ),
    tok.NE: (kind.EQOP, op.NE),
    tok.EQ_STRICT: (kind.EQOP, op.NEW_EQ),
    tok.NE_STRICT: (kind.EQOP, op.NEW_NE),
}
def _equality_expression(t, allowin):
    return _binary_expression(t, _EQUALITY,
                              lambda t: _relational_expression(t, allowin))

def _bitwise_and_expression(t, allowin):
    left = _equality_expression(t, allowin)
    while t.peek().tok == tok.BIT_AND:
        t.advance()
        right = _equality_expression(t, allowin)
        left = ParseNode(kind.BITAND, op.BITAND,
                         left.startpos, right.endpos,
                         None, [left, right])
    return left

def _bitwise_xor_expression(t, allowin):
    left = _bitwise_and_expression(t, allowin)
    while t.peek().tok == tok.BIT_XOR:
        t.advance()
        right = _bitwise_and_expression(t, allowin)
        left = ParseNode(kind.BITXOR, op.BITXOR,
                         left.startpos, right.endpos,
                         None, [left, right])
    return left

def _bitwise_or_expression(t, allowin):
    left = _bitwise_xor_expression(t, allowin)
    while t.peek().tok == tok.BIT_OR:
        t.advance()
        right = _bitwise_xor_expression(t, allowin)
        left = ParseNode(kind.BITOR, op.BITOR,
                         left.startpos, right.endpos,
                         None, [left, right])
    return left

def _logical_and_expression(t, allowin):
    exprs = []
    while True:
        exprs.append(_bitwise_or_expression(t, allowin))
        if t.peek().tok == tok.LOGICAL_AND:
            t.expect(tok.LOGICAL_AND)
        else:
            break

    while len(exprs) > 1:
        right = exprs.pop()
        left = exprs[-1]
        exprs[-1] = ParseNode(kind.AND, op.AND,
                              left.startpos, right.endpos,
                            None, [left, right])
    return exprs[0]

def _logical_or_expression(t, allowin):
    exprs = []
    while True:
        exprs.append(_logical_and_expression(t, allowin))
        if t.peek().tok == tok.LOGICAL_OR:
            t.expect(tok.LOGICAL_OR)
        else:
            break

    while len(exprs) > 1:
        right = exprs.pop()
        left = exprs[-1]
        exprs[-1] = ParseNode(kind.OR, op.OR,
                              left.startpos, right.endpos,
                            None, [left, right])
    return exprs[0]

def _conditional_expression(t, allowin):
    kid = _logical_or_expression(t, allowin)
    if t.peek().tok == tok.QUESTION:
        t.expect(tok.QUESTION)
        if_ = _assignment_expression(t, True)
        t.expect(tok.COLON)
        else_ = _assignment_expression(t, allowin)
        return ParseNode(kind.HOOK, None,
                         kid.startpos, else_.endpos,
                         None, [kid, if_, else_])
    else:
        return kid

_ASSIGNS = {
    tok.ASSIGN: (kind.ASSIGN, None),
    tok.ASSIGN_URSHIFT: (kind.ASSIGN, op.URSH),
    tok.ASSIGN_LSHIFT: (kind.ASSIGN, op.LSH),
    tok.ASSIGN_RSHIFT: (kind.ASSIGN, op.RSH),
    tok.ASSIGN_ADD: (kind.ASSIGN, op.ADD),
    tok.ASSIGN_SUB: (kind.ASSIGN, op.SUB),
    tok.ASSIGN_MUL: (kind.ASSIGN, op.MUL),
    tok.ASSIGN_MOD: (kind.ASSIGN, op.MOD),
    tok.ASSIGN_BIT_AND: (kind.ASSIGN, op.BITAND),
    tok.ASSIGN_BIT_OR: (kind.ASSIGN, op.BITOR),
    tok.ASSIGN_BIT_XOR: (kind.ASSIGN, op.BITXOR),
    tok.ASSIGN_DIV: (kind.ASSIGN, op.DIV),
}
def _assignment_expression(t, allowin):
    left = _conditional_expression(t, allowin)
    if t.peek().tok in _ASSIGNS:
        kid = left
        while kid.kind == kind.RP:
            kid, = kid.kids
        if kid.kind == kind.NAME:
            assert kid.opcode == op.NAME
            kid.opcode = op.SETNAME
        elif kid.kind == kind.DOT:
            assert kid.opcode == op.GETPROP, left.op
            kid.opcode = op.SETPROP
        elif kid.kind == kind.LB:
            assert kid.opcode == op.GETELEM
            kid.opcode = op.SETELEM
        elif kid.kind == kind.LP:
            assert kid.opcode == op.CALL
            kid.opcode = op.SETCALL
        else:
            raise JSSyntaxError(left.startpos, 'invalid_assign')
        kind_, op_ = _ASSIGNS[t.peek().tok]
        t.advance()
        right = _assignment_expression(t, allowin)
        return ParseNode(kind_, op_,
                         left.startpos, right.endpos, None, [left, right])
    else:
        return left

def _expression(t, allowin):
    items = []
    items.append(_assignment_expression(t, allowin))
    while t.peek().tok == tok.COMMA:
        t.advance()
        items.append(_assignment_expression(t, allowin))
    if len(items) > 1:
        return ParseNode(kind.COMMA, None, items[0].startpos,
                         items[-1].endpos, None, items)
    else:
        return items[0]

def _variable_declaration(t, allowin):
    nodes = []
    while True:
        x = t.expect(tok.NAME)
        value = None
        if t.peek().tok == tok.ASSIGN:
            t.advance()
            value = _assignment_expression(t, allowin)
        nodes.append(ParseNode(kind.NAME, op.SETNAME if value else op.NAME,
                               x.startpos,
                               value.endpos if value else x.endpos,
                               x.atom, [value]))

        if t.peek().tok == tok.COMMA:
            t.advance()
        else:
            return nodes

def _block_statement(t):
    kids = []
    startpos = t.expect(tok.LBRACE).startpos
    while t.peek().tok != tok.RBRACE:
        kids.append(_statement(t))
    endpos = t.expect(tok.RBRACE).endpos
    return ParseNode(kind.LC, None, startpos, endpos, None, kids)

def _empty_statement(t):
    # EMPTY STATEMENT
    x = t.expect(tok.SEMI)
    return ParseNode(kind.SEMI, None, x.startpos, x.endpos, None, [None])

def _var_statement(t):
    # VARIABLE STATEMENT
    startpos = t.expect(tok.VAR).startpos
    nodes = _variable_declaration(t, True)
    return _auto_semicolon(t, kind.VAR, op.DEFVAR,
                           startpos, nodes[-1].endpos, None, nodes)

def _if_statement(t):
    # IF STATEMENT
    startpos = t.expect(tok.IF).startpos
    t.expect(tok.LPAREN)
    condition = _expression(t, True)
    t.expect(tok.RPAREN)
    if_body = _statement(t)
    if t.peek().tok == tok.ELSE:
        t.advance()
        else_body = _statement(t)
    else:
        else_body = None
    endpos = else_body.endpos if else_body else if_body.endpos
    return ParseNode(kind.IF, None, startpos,
                     endpos, None, [condition, if_body, else_body])

def _do_statement(t):
    startpos = t.expect(tok.DO).startpos
    code = _statement(t)
    t.expect(tok.WHILE)
    t.expect(tok.LPAREN)
    expr = _expression(t, True)
    endtoken = t.expect(tok.RPAREN)
    return _auto_semicolon(t, kind.DO, None,
                           startpos, endtoken.endpos, None, [code, expr])

def _while_statement(t):
    startpos = t.expect(tok.WHILE).startpos
    t.expect(tok.LPAREN)
    expr = _expression(t, True)
    t.expect(tok.RPAREN)
    code = _statement(t)
    return ParseNode(kind.WHILE, None,
                     startpos, code.endpos, None, [expr, code])

def _for_statement(t):
    for_startpos = t.expect(tok.FOR).startpos
    t.expect(tok.LPAREN)

    for_exprs = []
    if t.peek().tok == tok.VAR:
        var_startpos = t.advance().startpos
        kids = _variable_declaration(t, False)
        vars = ParseNode(kind.VAR, op.DEFVAR, var_startpos, kids[-1].endpos,
                         None, kids)

        if t.peek().tok == tok.IN:
            t.advance()
            in_ = _expression(t, True)
            for_exprs = [vars, in_]
        else:
            for_exprs = [vars, None, None]
    else:
        if t.peek().tok != tok.SEMI:
            expr = _expression(t, False)
        else:
            expr = None

        if t.peek().tok == tok.IN:
            t.advance()
            vars = expr
            in_ = _expression(t, True)
            for_exprs = [vars, in_]
        else:
            for_exprs = [expr, None, None]

    if len(for_exprs) == 2:
        condition = ParseNode(kind.IN, None, for_exprs[0].startpos,
                              for_exprs[-1].endpos, None, for_exprs)
    else:
        x = t.expect(tok.SEMI)
        if t.peek().tok != tok.SEMI:
            for_exprs[1] = _expression(t, True)
        t.expect(tok.SEMI)
        if t.peek().tok != tok.RPAREN:
            for_exprs[2] = _expression(t, True)
        condition = ParseNode(kind.RESERVED, None, None, None,
                              None, for_exprs)

    t.expect(tok.RPAREN)
    body = _statement(t)
    return ParseNode(kind.FOR,
                     op.FORIN if condition.kind == kind.IN else None,
                     for_startpos, body.endpos,
                     None, [condition, body])

def _continue_statement(t):
    endtoken = t.expect(tok.CONTINUE)
    startpos = endtoken.startpos

    if t.peek_sameline().tok == tok.NAME:
        endtoken = t.expect(tok.NAME)
        name = endtoken.atom
    else:
        name = None
    # TODO: Validate Scope Labels
    return _auto_semicolon(t, kind.CONTINUE, None, startpos, endtoken.endpos, name, [])

def _break_statement(t):
    endtoken = t.expect(tok.BREAK)
    startpos = endtoken.startpos

    if t.peek_sameline().tok == tok.NAME:
        endtoken = t.expect(tok.NAME)
        name = endtoken.atom
    else:
        name = None
    # TODO: Validate Scope Labels
    return _auto_semicolon(t, kind.BREAK, None, startpos, endtoken.endpos, name, [])

def _return_statement(t):
    endtoken = t.expect(tok.RETURN)
    startpos = endtoken.startpos

    if t.peek_sameline().tok not in (tok.EOF, tok.EOL, tok.SEMI, tok.RBRACE):
        expr = _expression(t, True)
        endtoken = expr
    else:
        expr = None
    # TODO: Validate Scope Labels
    return _auto_semicolon(t, kind.RETURN, None, startpos, endtoken.endpos,
                     None, [expr])

def _with_statement(t):
    startpos = t.expect(tok.WITH).startpos
    t.expect(tok.LPAREN)
    expr = _expression(t, True)
    t.expect(tok.RPAREN)
    body = _statement(t)
    return ParseNode(kind.WITH, None, startpos, body.endpos, None, [expr, body])

def _switch_statement(t):
    switch_startpos = t.expect(tok.SWITCH).startpos
    t.expect(tok.LPAREN)
    expr = _expression(t, True)
    t.expect(tok.RPAREN)
    lc_startpos = t.expect(tok.LBRACE).startpos
    cases = []
    while t.peek().tok != tok.RBRACE:
        case_kind = None
        case_expr = None
        if t.peek().tok == tok.CASE:
            case_startpos = t.advance().startpos
            case_kind = kind.CASE
            case_expr = _expression(t, True)
        elif t.peek().tok == tok.DEFAULT:
            case_startpos = t.advance().startpos
            case_kind = kind.DEFAULT
        else:
            raise JSSyntaxError(t.peek().startpos, 'invalid_case')

        case_endpos = t.expect(tok.COLON).endpos

        statements = []
        while t.peek().tok not in (tok.DEFAULT, tok.CASE, tok.RBRACE):
            statements.append(_statement(t))
        if statements:
            statements_startpos = statements[0].startpos
            statements_endpos = statements[-1].endpos
            case_endpos = statements[-1].endpos
        else:
            statements_startpos = case_endpos
            statements_endpos = case_endpos

        cases.append(ParseNode(case_kind, None, case_startpos, case_endpos,
                               None, [
            case_expr,
            ParseNode(kind.LC, None, statements_startpos,
                      statements_endpos, None, statements)
        ]))

    rc_endpos = t.expect(tok.RBRACE).endpos
    return ParseNode(kind.SWITCH, None, switch_startpos, rc_endpos,
                     None, [expr,
                ParseNode(kind.LC, None, lc_startpos, rc_endpos, None, cases)])

def _throw_statement(t):
    # TODO: Validate Scope
    startpos = t.expect(tok.THROW).startpos
    if t.peek_sameline().tok == tok.EOL:
        raise JSSyntaxError(t.peek_sameline().startpos, 'expected_statement')
    expr = _expression(t, True)
    return _auto_semicolon(t, kind.THROW, op.THROW, startpos, expr.endpos,
                           None, [expr])

def _try_statement(t):
    try_startpos = t.expect(tok.TRY).startpos

    try_node = _block_statement(t)
    catch_node = None
    finally_node = None
    try_endpos = None

    if t.peek().tok == tok.CATCH:
        catch_startpos = t.advance().startpos
        t.expect(tok.LPAREN)
        x = t.expect(tok.NAME)
        catch_expr = ParseNode(kind.NAME, None, x.startpos, x.endpos,
                               x.atom, [None])
        t.expect(tok.RPAREN)
        catch_block = _block_statement(t)
        catch_endpos = catch_block.endpos
        catch_node = \
            ParseNode(kind.RESERVED, None, None, None, None, [
                ParseNode(kind.LEXICALSCOPE, op.LEAVEBLOCK,
                          catch_startpos, catch_endpos, None, [
                    ParseNode(kind.CATCH, None, catch_startpos,
                              catch_endpos, None,
                       [catch_expr, None, catch_block])
                ])
            ])
        try_endpos = catch_endpos

    if t.peek().tok == tok.FINALLY:
        t.advance()
        finally_node = _block_statement(t)
        try_endpos = finally_node.endpos

    if not catch_node and not finally_node:
        raise JSSyntaxError(try_endpos, 'invalid_catch')

    return ParseNode(kind.TRY, None, try_startpos, try_endpos,
                     None,
                     [try_node, catch_node, finally_node])

def _statement(t):
    # TODO: Labelled Statement
    x = t.peek()
    if x.tok == tok.LBRACE:
        return _block_statement(t)
    elif x.tok == tok.SEMI:
        return _empty_statement(t)
    elif x.tok == tok.VAR:
        return _var_statement(t)
    elif x.tok == tok.IF:
        return _if_statement(t)
    elif x.tok == tok.DO:
        return _do_statement(t)
    elif x.tok == tok.WHILE:
        return _while_statement(t)
    elif x.tok == tok.FOR:
        return _for_statement(t)
    elif x.tok == tok.CONTINUE:
        return _continue_statement(t)
    elif x.tok == tok.BREAK:
        return _break_statement(t)
    elif x.tok == tok.RETURN:
        return _return_statement(t)
    elif x.tok == tok.WITH:
        return _with_statement(t)
    elif x.tok == tok.SWITCH:
        return _switch_statement(t)
    elif x.tok == tok.THROW:
        return _throw_statement(t)
    elif x.tok == tok.TRY:
        return _try_statement(t)
    elif x.tok == tok.EOF:
        raise JSSyntaxError(x.startpos, 'unexpected_eof')
    elif x.tok == tok.FUNCTION:
        return _function_declaration(t, op.CLOSURE) #TODO: warn, since this is not reliable

    elif x.tok not in (tok.LBRACE, tok.FUNCTION):
        expr = _expression(t, True)
        if expr.kind == tok.NAME and t.peek().tok == tok.COLON:
            t.expect(tok.COLON)
            stmt = _statement(t)
            return ParseNode(kind.COLON, op.NAME, expr.startpos,
                             stmt.endpos, expr.atom, [stmt])

        return _auto_semicolon(t, kind.SEMI, None, expr.startpos, expr.endpos,
                               None, [expr])
    else:
        raise JSSyntaxError(x.startpos, 'syntax_error')

def _sourceelements(t, end_tok):
    nodes = []
    while True:
        x = t.peek()
        if x.tok == tok.FUNCTION:
            nodes.append(_function_declaration(t, None))
        elif x.tok == end_tok:
            return nodes
        else:
            nodes.append(_statement(t))

def parsestring(s, startpos=None):
    stream = tokenizer.TokenStream(s, startpos)
    t = tokenizer.Tokenizer(stream)
    nodes = _sourceelements(t, tok.EOF)
    lc_endpos = t.expect(tok.EOF).endpos
    lc_startpos = nodes[-1].startpos if nodes else lc_endpos
    return ParseNode(kind.LC, None, lc_startpos, lc_endpos, None, nodes)

def is_valid_version(version):
    return version in _VERSIONS

def _validate(node, depth=0):
    for kid in node.kids:
        if kid:
            assert kid.parent is node
            _validate(kid, depth+1)

def parse(script, jsversion,
          error_callback, startpos):
    # TODO: respect version
    assert is_valid_version(jsversion)
    try:
        root = parsestring(script, startpos)
    except JSSyntaxError as error:
        error_callback(error.pos.line, error.pos.col, error.msg, error.msg_args)
        return None
    _validate(root)
    return root

def is_compilable_unit(script, jsversion):
    # TODO: respect version
    assert is_valid_version(jsversion)
    try:
        parsestring(script)
    except JSSyntaxError as error:
        return error.msg not in ('unexpected_eof', 'unterminated_comment')
    return True

class TestParser(unittest.TestCase):
    def testCompilableUnit(self):
        self.assert_(is_compilable_unit('', 'default'))
        self.assert_(is_compilable_unit('/**/', 'default'))
        self.assert_(not is_compilable_unit('/*', 'default'))
    def testUnterminatedComment(self):
        try:
            parsestring('/*')
        except JSSyntaxError as error:
            self.assertEqual(error.pos, NodePos(0,1))
        else:
            self.assert_(False)
    def testObjectEndComma(self):
        root = parsestring('a={a:1,}')
        node, = root.kids
        self.assertEquals(node.kind, kind.SEMI)
        node, = node.kids
        self.assertEquals(node.kind, kind.ASSIGN)
        left, right = node.kids
        self.assertEquals(left.atom, 'a')
        self.assertEquals(right.kind, kind.RC)
        node = right.end_comma
        self.assertEquals(node.kind, tok.COMMA)
        self.assertEquals(node.startpos, NodePos(0, 6))
        self.assertEquals(node.endpos, NodePos(0, 6))
    def _testArrayEndComma(self, script, col):
        root = parsestring(script)
        node, = root.kids
        self.assertEquals(node.kind, kind.SEMI)
        node, = node.kids
        self.assertEquals(node.kind, kind.ASSIGN)
        left, right = node.kids
        self.assertEquals(left.atom, 'a')
        self.assertEquals(right.kind, kind.RB)
        node = right.end_comma
        self.assertEquals(node is None, col is None)
        if col is None:
            self.assert_(node is None)
        else:
            self.assertEquals(node.kind, tok.COMMA)
            self.assertEquals(node.startpos, NodePos(0, col))
            self.assertEquals(node.endpos, NodePos(0, col))
    def testArrayEndComma(self):
        self._testArrayEndComma('a=[,]', 3)
        self._testArrayEndComma('a=[a,]', 4)
        self._testArrayEndComma('a=[a,b,c]', None)
    def _testArrayCommas(self, script, items, end_comma):
        root = parsestring(script)
        node, = root.kids
        self.assertEquals(node.kind, kind.SEMI)
        node, = node.kids
        self.assertEquals(node.kind, kind.ASSIGN)
        left, right = node.kids
        self.assertEquals(left.atom, 'a')
        self.assertEquals(right.kind, kind.RB)
        node = right
        self.assertEquals(len(node.kids), len(items))
        for kid, item in zip(node.kids, items):
            self.assertEquals(kid.atom, item)
        self.assertEquals(bool(node.end_comma), end_comma)
    def testArrayCommas(self):
        self._testArrayCommas('a=[]', [], False)
        self._testArrayCommas('a=[,]', [None], True)
        self._testArrayCommas('a=[,,]', [None, None], True)
        self._testArrayCommas('a=[,1]', [None, '1'], False)
        self._testArrayCommas('a=[,,1]', [None, None, '1'], False)
        self._testArrayCommas('a=[1,,1]', ['1', None, '1'], False)
        self._testArrayCommas('a=[,1,]', [None, '1'], True)
    def testParseArray(self):
        try:
            parsestring('a=[1 1]')
        except JSSyntaxError as error:
            pass
        else:
            self.assert_(False)
