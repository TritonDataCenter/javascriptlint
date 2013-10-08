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

def _auto_semicolon(t, kind_, op_, start_offset, end_offset, atom, kids):
    nosemi = False
    if t.peek_sameline().tok not in (tok.EOF, tok.EOL, tok.RBRACE):
        x = t.advance()
        if x.tok != tok.SEMI:
            raise JSSyntaxError(x.start_offset, 'semi_before_stmnt')
        end_offset = x.end_offset
    else:
        nosemi = True
    return ParseNode(kind_, op_, start_offset, end_offset, atom, kids, nosemi)

def _function_arglist(t):
    fn_args = []
    if t.peek().tok != tok.RPAREN:
        while True:
            x = t.expect(tok.NAME)
            fn_args.append(ParseNode(kind.NAME, op.ARGNAME,
                                     x.start_offset,
                                     x.end_offset, x.atom, []))
            if t.peek().tok == tok.COMMA:
                t.advance()
            else:
                break
    return fn_args

def _primary_expression(t):
    x = t.next_withregexp()
    if x.tok == tok.THIS:
        return ParseNode(kind.PRIMARY, op.THIS, x.start_offset, x.end_offset, None, [])
    elif x.tok == tok.NAME:
        return ParseNode(kind.NAME, op.NAME, x.start_offset, x.end_offset, x.atom, [None])
    elif x.tok == tok.NULL:
        return ParseNode(kind.PRIMARY, op.NULL, x.start_offset, x.end_offset, None, [])
    elif x.tok == tok.TRUE:
        return ParseNode(kind.PRIMARY, op.TRUE, x.start_offset, x.end_offset, None, [])
    elif x.tok == tok.FALSE:
        return ParseNode(kind.PRIMARY, op.FALSE, x.start_offset, x.end_offset, None, [])
    elif x.tok == tok.STRING:
        return ParseNode(kind.STRING, op.STRING, x.start_offset, x.end_offset, x.atom, [])
    elif x.tok == tok.REGEXP:
        return ParseNode(kind.OBJECT, op.REGEXP, x.start_offset, x.end_offset, None, [])
    elif x.tok == tok.NUMBER:
        return ParseNode(kind.NUMBER, None, x.start_offset, x.end_offset, x.atom, [])
    elif x.tok == tok.LBRACKET:
        start_offset = x.start_offset
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
                                  x.start_offset, x.end_offset, None, [])
                items[-1] = items[-1] or comma

                # Check for the end.
                if t.peek().tok == tok.RBRACKET:
                    end_comma = comma
                    break
        end_offset = t.expect(tok.RBRACKET).end_offset
        return ParseNode(kind.RB, None, start_offset, end_offset, None, items,
                         end_comma=end_comma)
    elif x.tok == tok.LBRACE:
        start_offset = x.start_offset
        kids = []
        # TODO: get/set
        end_comma = None
        while True:
            x = t.peek()
            if x.tok == tok.RBRACE:
                break
            elif x.tok == tok.STRING:
                t.expect(tok.STRING)
                key = ParseNode(kind.STRING, None, x.start_offset,
                                x.end_offset, x.atom, [])
            elif x.tok == tok.NUMBER:
                t.expect(tok.NUMBER)
                key = ParseNode(kind.NUMBER, None, x.start_offset,
                                x.end_offset, x.atom, [])
            else:
                x = t.expect_identifiername()
                key = ParseNode(kind.NAME, None, x.start_offset, x.end_offset,
                                x.atom, [])
            t.expect(tok.COLON)
            value = _assignment_expression(t, True)
            kids.append(ParseNode(kind.COLON, None, key.start_offset,
                                  value.end_offset, None, [key, value]))
            if t.peek().tok == tok.COMMA:
                x = t.advance()
                end_comma = ParseNode(kind.COMMA, None,
                                      x.start_offset, x.end_offset, None, [])
            else:
                end_comma = None
                break
        end_offset = t.expect(tok.RBRACE).end_offset
        return ParseNode(kind.RC, None, start_offset, end_offset, None, kids,
                         end_comma=end_comma)
    elif x.tok == tok.LPAREN:
        start_offset = x.start_offset
        kid = _expression(t, True)
        end_offset = t.expect(tok.RPAREN).end_offset
        return ParseNode(kind.RP, None, start_offset, end_offset, None, [kid])
    else:
        raise JSSyntaxError(x.start_offset, 'syntax_error')

def _function_declaration(t, named_opcode):
    node = _function_expression(t, named_opcode)

    # Convert anonymous functions in expressions.
    if node.opcode == op.ANONFUNOBJ:
        node = _auto_semicolon(t, kind.SEMI, None, node.start_offset, node.end_offset,
                               None, [node])
    return node


def _function_expression(t, named_opcode):
    start_offset = t.expect(tok.FUNCTION).start_offset
    if t.peek().tok == tok.NAME:
        fn_name = t.expect(tok.NAME).atom
        opcode = named_opcode
    else:
        fn_name = None
        opcode = op.ANONFUNOBJ
    t.expect(tok.LPAREN)
    fn_args = _function_arglist(t)
    t.expect(tok.RPAREN)
    fn_body_start_offset = t.expect(tok.LBRACE).start_offset
    kids = _sourceelements(t, tok.RBRACE)
    fn_body_end_offset = t.expect(tok.RBRACE).end_offset
    fn_body = ParseNode(kind.LC, None, fn_body_start_offset,
                        fn_body_end_offset, None, kids)
    return ParseNode(kind.FUNCTION, opcode, start_offset, fn_body.end_offset,
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
    start_offset = t.expect(tok.NEW).start_offset
    expr = _member_expression(t)
    # If no (), this is a variant of the NewExpression
    if t.peek().tok == tok.LPAREN:
        t.expect(tok.LPAREN)
        args = _argument_list(t)
        end_offset = t.expect(tok.RPAREN).end_offset
    else:
        args = []
        end_offset = expr.end_offset
    return ParseNode(kind.NEW, op.NEW, start_offset, end_offset,
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
            end_offset = t.expect(tok.RBRACKET).end_offset
            kid = ParseNode(kind.LB, op.GETELEM, kid.start_offset, end_offset,
                            None, [kid, expr])
        elif t.peek().tok == tok.DOT:
            t.advance()
            expr = t.expect_identifiername()
            kid = ParseNode(kind.DOT, op.GETPROP, kid.start_offset, expr.end_offset,
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
            end_offset = t.expect(tok.RPAREN).end_offset
            expr = ParseNode(kind.LP, op.CALL, expr.start_offset,
                             end_offset, None, [expr] + args)
        elif x.tok == tok.LBRACKET:
            t.expect(tok.LBRACKET)
            lookup = _expression(t, True)
            end_offset = t.expect(tok.RBRACKET).end_offset
            expr = ParseNode(kind.LB, op.GETELEM,
                             expr.start_offset, end_offset,
                             None, [expr, lookup])
        elif x.tok == tok.DOT:
            t.expect(tok.DOT)
            lookup = t.expect_identifiername()
            expr = ParseNode(kind.DOT, op.GETPROP,
                             expr.start_offset, lookup.end_offset,
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
        end_offset = t.expect(tok.INC).end_offset
        if kid.kind == kind.DOT and kid.opcode == op.GETPROP:
            opcode = op.PROPINC
        else:
            opcode = op.NAMEINC
        return ParseNode(kind.INC, opcode,
                         kid.start_offset, end_offset, None, [kid])
    elif t.peek_sameline().tok == tok.DEC:
        end_offset = t.expect(tok.DEC).end_offset
        return ParseNode(kind.DEC, op.NAMEDEC,
                         kid.start_offset, end_offset, None, [kid])
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
        start_offset = t.advance().start_offset
        kid = _unary_expression(t)
        return ParseNode(kind_, op_, start_offset, kid.end_offset, None, [kid])
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
                         kids[0].start_offset, kids[1].end_offset,
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
                         left.start_offset, right.end_offset,
                         None, [left, right])
    return left

def _bitwise_xor_expression(t, allowin):
    left = _bitwise_and_expression(t, allowin)
    while t.peek().tok == tok.BIT_XOR:
        t.advance()
        right = _bitwise_and_expression(t, allowin)
        left = ParseNode(kind.BITXOR, op.BITXOR,
                         left.start_offset, right.end_offset,
                         None, [left, right])
    return left

def _bitwise_or_expression(t, allowin):
    left = _bitwise_xor_expression(t, allowin)
    while t.peek().tok == tok.BIT_OR:
        t.advance()
        right = _bitwise_xor_expression(t, allowin)
        left = ParseNode(kind.BITOR, op.BITOR,
                         left.start_offset, right.end_offset,
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
                              left.start_offset, right.end_offset,
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
                              left.start_offset, right.end_offset,
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
                         kid.start_offset, else_.end_offset,
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
            raise JSSyntaxError(left.start_offset, 'invalid_assign')
        kind_, op_ = _ASSIGNS[t.peek().tok]
        t.advance()
        right = _assignment_expression(t, allowin)
        return ParseNode(kind_, op_,
                         left.start_offset, right.end_offset, None, [left, right])
    else:
        return left

def _expression(t, allowin):
    items = []
    items.append(_assignment_expression(t, allowin))
    while t.peek().tok == tok.COMMA:
        t.advance()
        items.append(_assignment_expression(t, allowin))
    if len(items) > 1:
        return ParseNode(kind.COMMA, None, items[0].start_offset,
                         items[-1].end_offset, None, items)
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
                               x.start_offset,
                               value.end_offset if value else x.end_offset,
                               x.atom, [value]))

        if t.peek().tok == tok.COMMA:
            t.advance()
        else:
            return nodes

def _block_statement(t):
    kids = []
    start_offset = t.expect(tok.LBRACE).start_offset
    while t.peek().tok != tok.RBRACE:
        kids.append(_statement(t))
    end_offset = t.expect(tok.RBRACE).end_offset
    return ParseNode(kind.LC, None, start_offset, end_offset, None, kids)

def _empty_statement(t):
    # EMPTY STATEMENT
    x = t.expect(tok.SEMI)
    return ParseNode(kind.SEMI, None, x.start_offset, x.end_offset, None, [None])

def _var_statement(t):
    # VARIABLE STATEMENT
    start_offset = t.expect(tok.VAR).start_offset
    nodes = _variable_declaration(t, True)
    return _auto_semicolon(t, kind.VAR, op.DEFVAR,
                           start_offset, nodes[-1].end_offset, None, nodes)

def _if_statement(t):
    # IF STATEMENT
    start_offset = t.expect(tok.IF).start_offset
    t.expect(tok.LPAREN)
    condition = _expression(t, True)
    t.expect(tok.RPAREN)
    if_body = _statement(t)
    if t.peek().tok == tok.ELSE:
        t.advance()
        else_body = _statement(t)
    else:
        else_body = None
    end_offset = else_body.end_offset if else_body else if_body.end_offset
    return ParseNode(kind.IF, None, start_offset,
                     end_offset, None, [condition, if_body, else_body])

def _do_statement(t):
    start_offset = t.expect(tok.DO).start_offset
    code = _statement(t)
    t.expect(tok.WHILE)
    t.expect(tok.LPAREN)
    expr = _expression(t, True)
    endtoken = t.expect(tok.RPAREN)
    return _auto_semicolon(t, kind.DO, None,
                           start_offset, endtoken.end_offset, None, [code, expr])

def _while_statement(t):
    start_offset = t.expect(tok.WHILE).start_offset
    t.expect(tok.LPAREN)
    expr = _expression(t, True)
    t.expect(tok.RPAREN)
    code = _statement(t)
    return ParseNode(kind.WHILE, None,
                     start_offset, code.end_offset, None, [expr, code])

def _for_statement(t):
    for_start_offset = t.expect(tok.FOR).start_offset
    t.expect(tok.LPAREN)

    for_exprs = []
    if t.peek().tok == tok.VAR:
        var_start_offset = t.advance().start_offset
        kids = _variable_declaration(t, False)
        vars = ParseNode(kind.VAR, op.DEFVAR, var_start_offset, kids[-1].end_offset,
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
        condition = ParseNode(kind.IN, None, for_exprs[0].start_offset,
                              for_exprs[-1].end_offset, None, for_exprs)
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
                     for_start_offset, body.end_offset,
                     None, [condition, body])

def _continue_statement(t):
    endtoken = t.expect(tok.CONTINUE)
    start_offset = endtoken.start_offset

    if t.peek_sameline().tok == tok.NAME:
        endtoken = t.expect(tok.NAME)
        name = endtoken.atom
    else:
        name = None
    # TODO: Validate Scope Labels
    return _auto_semicolon(t, kind.CONTINUE, None, start_offset, endtoken.end_offset, name, [])

def _break_statement(t):
    endtoken = t.expect(tok.BREAK)
    start_offset = endtoken.start_offset

    if t.peek_sameline().tok == tok.NAME:
        endtoken = t.expect(tok.NAME)
        name = endtoken.atom
    else:
        name = None
    # TODO: Validate Scope Labels
    return _auto_semicolon(t, kind.BREAK, None, start_offset, endtoken.end_offset, name, [])

def _return_statement(t):
    endtoken = t.expect(tok.RETURN)
    start_offset = endtoken.start_offset

    if t.peek_sameline().tok not in (tok.EOF, tok.EOL, tok.SEMI, tok.RBRACE):
        expr = _expression(t, True)
        endtoken = expr
    else:
        expr = None
    # TODO: Validate Scope Labels
    return _auto_semicolon(t, kind.RETURN, None, start_offset, endtoken.end_offset,
                     None, [expr])

def _with_statement(t):
    start_offset = t.expect(tok.WITH).start_offset
    t.expect(tok.LPAREN)
    expr = _expression(t, True)
    t.expect(tok.RPAREN)
    body = _statement(t)
    return ParseNode(kind.WITH, None, start_offset, body.end_offset, None, [expr, body])

def _switch_statement(t):
    switch_start_offset = t.expect(tok.SWITCH).start_offset
    t.expect(tok.LPAREN)
    expr = _expression(t, True)
    t.expect(tok.RPAREN)
    lc_start_offset = t.expect(tok.LBRACE).start_offset
    cases = []
    while t.peek().tok != tok.RBRACE:
        case_kind = None
        case_expr = None
        if t.peek().tok == tok.CASE:
            case_start_offset = t.advance().start_offset
            case_kind = kind.CASE
            case_expr = _expression(t, True)
        elif t.peek().tok == tok.DEFAULT:
            case_start_offset = t.advance().start_offset
            case_kind = kind.DEFAULT
        else:
            raise JSSyntaxError(t.peek().start_offset, 'invalid_case')

        case_end_offset = t.expect(tok.COLON).end_offset

        statements = []
        while t.peek().tok not in (tok.DEFAULT, tok.CASE, tok.RBRACE):
            statements.append(_statement(t))
        if statements:
            statements_start_offset = statements[0].start_offset
            statements_end_offset = statements[-1].end_offset
            case_end_offset = statements[-1].end_offset
        else:
            statements_start_offset = case_end_offset
            statements_end_offset = case_end_offset

        cases.append(ParseNode(case_kind, None, case_start_offset, case_end_offset,
                               None, [
            case_expr,
            ParseNode(kind.LC, None, statements_start_offset,
                      statements_end_offset, None, statements)
        ]))

    rc_end_offset = t.expect(tok.RBRACE).end_offset
    return ParseNode(kind.SWITCH, None, switch_start_offset, rc_end_offset,
                     None, [expr,
                ParseNode(kind.LC, None, lc_start_offset, rc_end_offset, None, cases)])

def _throw_statement(t):
    # TODO: Validate Scope
    start_offset = t.expect(tok.THROW).start_offset
    if t.peek_sameline().tok == tok.EOL:
        raise JSSyntaxError(t.peek_sameline().start_offset, 'expected_statement')
    expr = _expression(t, True)
    return _auto_semicolon(t, kind.THROW, op.THROW, start_offset, expr.end_offset,
                           None, [expr])

def _try_statement(t):
    try_start_offset = t.expect(tok.TRY).start_offset

    try_node = _block_statement(t)
    catch_node = None
    finally_node = None
    try_end_offset = None

    if t.peek().tok == tok.CATCH:
        catch_start_offset = t.advance().start_offset
        t.expect(tok.LPAREN)
        x = t.expect(tok.NAME)
        catch_expr = ParseNode(kind.NAME, None, x.start_offset, x.end_offset,
                               x.atom, [None])
        t.expect(tok.RPAREN)
        catch_block = _block_statement(t)
        catch_end_offset = catch_block.end_offset
        catch_node = \
            ParseNode(kind.RESERVED, None, None, None, None, [
                ParseNode(kind.LEXICALSCOPE, op.LEAVEBLOCK,
                          catch_start_offset, catch_end_offset, None, [
                    ParseNode(kind.CATCH, None, catch_start_offset,
                              catch_end_offset, None,
                       [catch_expr, None, catch_block])
                ])
            ])
        try_end_offset = catch_end_offset

    if t.peek().tok == tok.FINALLY:
        t.advance()
        finally_node = _block_statement(t)
        try_end_offset = finally_node.end_offset

    if not catch_node and not finally_node:
        raise JSSyntaxError(try_end_offset, 'invalid_catch')

    return ParseNode(kind.TRY, None, try_start_offset, try_end_offset,
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
        raise JSSyntaxError(x.start_offset, 'unexpected_eof')
    elif x.tok == tok.FUNCTION:
        return _function_declaration(t, op.CLOSURE) #TODO: warn, since this is not reliable

    elif x.tok not in (tok.LBRACE, tok.FUNCTION):
        expr = _expression(t, True)
        if expr.kind == tok.NAME and t.peek().tok == tok.COLON:
            t.expect(tok.COLON)
            stmt = _statement(t)
            return ParseNode(kind.COLON, op.NAME, expr.start_offset,
                             stmt.end_offset, expr.atom, [stmt])

        return _auto_semicolon(t, kind.SEMI, None, expr.start_offset, expr.end_offset,
                               None, [expr])
    else:
        raise JSSyntaxError(x.start_offset, 'syntax_error')

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

def parsestring(s, start_offset=0):
    assert not start_offset is None
    stream = tokenizer.TokenStream(s, start_offset)
    t = tokenizer.Tokenizer(stream)
    nodes = _sourceelements(t, tok.EOF)
    lc_end_offset = t.expect(tok.EOF).end_offset
    lc_start_offset = nodes[-1].start_offset if nodes else lc_end_offset
    return ParseNode(kind.LC, None, lc_start_offset, lc_end_offset, None, nodes)

def is_valid_version(version):
    return version in _VERSIONS

def _validate(node, depth=0):
    for kid in node.kids:
        if kid:
            assert kid.parent is node
            _validate(kid, depth+1)

def parse(script, jsversion, error_callback, start_offset):
    # TODO: respect version
    assert is_valid_version(jsversion)
    try:
        root = parsestring(script, start_offset)
    except JSSyntaxError as error:
        error_callback(error.offset, error.msg, error.msg_args)
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
            self.assertEqual(error.pos, NodePos(0, 1))
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
        self.assertEquals(node.start_offset, NodePos(0, 6))
        self.assertEquals(node.end_offset, NodePos(0, 6))
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
            self.assertEquals(node.start_offset, NodePos(0, col))
            self.assertEquals(node.end_offset, NodePos(0, col))
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
