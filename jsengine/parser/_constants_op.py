# vim: sw=4 ts=4 et

_OPS = [
    'ADD',
    'AND',
    'ANONFUNOBJ',
    'ARGNAME',
    'BITAND',
    'BITNOT',
    'BITOR',
    'BITXOR',
    'CALL',
    'C_COMMENT',
    'CLOSURE',
    'CPP_COMMENT',
    'DECNAME',
    'DEFVAR',
    'DIV',
    'EQOP',
    'FALSE',
    'FORIN',
    'GETELEM',
    'GETPROP',
    'GT',
    'GE',
    'HOOK',
    'HTMLCOMMENT',
    'IN',
    'INCNAME',
    'INSTANCEOF',
    'LEAVEBLOCK',
    'LSH',
    'LT',
    'LE',
    'MOD',
    'MUL',
    'NAME',
    'NAMEDEC',
    'NAMEINC',
    'NAMEDFUNOBJ',
    'NEG',
    'NE',
    'NEW',
    'NEW_EQ',
    'NEW_NE',
    'NOT',
    'NULL',
    'NUMBER',
    'OR',
    'POS',
    'PROPINC',
    'REGEXP',
    'RSH',
    'SETCALL',
    'SETELEM',
    'SETNAME',
    'SETPROP',
    'STRING',
    'SUB',
    'THIS',
    'TRUE',
    'THROW',
    'TYPEOF',
    'URSH',
    'VOID',
    'EQ',
    'NAME',
    'REGEXP',
    'SETNAME',
    'VOID',
    'CALL',
]
class _Op(str):
    def __repr__(self):
        return 'op.%s' % self

class _Ops:
    NOP = None # TODO!
    def __init__(self):
        for op in _OPS:
            setattr(self, op, _Op(op))
    def contains(self, item):
        return isinstance(item, _Op) and \
            getattr(self, item) is item
op = _Ops()
