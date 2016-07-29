# vim: sw=4 ts=4 et

_MESSAGES = (
    'unexpected_eof',
    'semi_before_stmnt',
    'syntax_error',
    'unterminated_comment',
    'expected_tok',
    'unexpected_char',
)

class JSSyntaxError(BaseException):
    def __init__(self, offset, msg, msg_args=None):
        assert msg in _MESSAGES, msg
        self.offset = offset
        self.msg = msg
        self.msg_args = msg_args or {}
    def __unicode__(self):
        return '%s: %s' % (self.offset, self.msg)
    def __repr__(self):
        return 'JSSyntaxError(%r, %r, %r)' % (self.offset, self.msg. self.msg_args)
