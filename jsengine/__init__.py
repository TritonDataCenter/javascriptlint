# vim: sw=4 ts=4 et

_MESSAGES = (
    'eof',
    'semi_before_stmnt',
    'syntax_error',
    'unterminated_comment',
    'expected_tok',
    'unexpected_char',
)

class JSSyntaxError(BaseException):
    def __init__(self, pos, msg, msg_args=None):
        assert msg in _MESSAGES, msg
        self.pos = pos
        self.msg = msg
        self.msg_args = msg_args or {}
    def __unicode__(self):
        return '%s: %s' % (self.pos, self.msg)
    def __repr__(self):
        return 'JSSyntaxError(%r, %r, %r)' % (self.pos, self.msg. self.msg_args)
