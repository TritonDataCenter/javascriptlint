# vim: sw=4 ts=4 et

_KINDS = [
    'AND',
    'BITAND',
    'BITOR',
    'BITXOR',
    'CATCH',
    'COMMENT',
    'DELETE',
    'DIVOP',
    'DOT',
    'EQ',
    'FINALLY',
    'FUNCTION',
    'HOOK',
    'IF',
    'IN',
    'INC',
    'INSTANCEOF',
    'LB',
    'LC',
    'LEXICALSCOPE',
    'LP',
    'MINUS',
    'NAME',
    'NEW',
    'OBJECT',
    'OR',
    'PLUS',
    'PRIMARY',
    'RB',
    'RC',
    'RELOP',
    'RESERVED',
    'RP',
    'SEMI',
    'SHOP',
    'STAR',
    'TRY',
    'UNARYOP',
    'VAR',
    'ASSIGN',
    'CASE',
    'COLON',
    'DEFAULT',
    'EQOP',
    'OBJECT',
    'RELOP',
    'SWITCH',
    'WITH',
    'WHILE',
    'DO',
    'FOR',
    'COMMA',
    'DEC',
    'BREAK',
    'CONTINUE',
    'THROW',
    'RETURN',
    'UNARYOP',
    'LP',
    'NUMBER',
    'RB',
    'STRING',
    'YIELD', # TODO
]
class _Kind(str):
    def __repr__(self):
        return 'kind.%s' % self

class _Kinds:
    def __init__(self):
        for kind in _KINDS:
            setattr(self, kind, _Kind(kind))
    def contains(self, item):
        return isinstance(item, _Kind) and \
            getattr(self, item) is item
kind = _Kinds()
