# vim: sw=4 ts=4 et
from jsengine import JSSyntaxError
import tok

_WHITESPACE = u'\u0020\t\u000B\u000C\u00A0\uFFFF'
_LINETERMINATOR = u'\u000A\u000D\u2028\u2029'
_DIGITS = u'0123456789'
_HEX_DIGITS = _DIGITS + u'abcdefABCDEF'
_IDENT = u'abcdefghijklmnopqrstuvwxyz' + \
         u'ABCDEFGHIJKLMNOPQRSTUVWXYZ' + \
         u'$_'

class _Char(object):
    def __init__(self, u):
        assert isinstance(u, int) or u is None, u
        self._u = u

    @classmethod
    def fromstr(cls, s, i):
        return _Char(ord(s[i]))

    @classmethod
    def ord(cls, s):
        return _Char(ord(s))

    @property
    def uval(self):
        return self._u

    def tostr(self):
        if self._u is None:
            return unicode()
        return unichr(self._u)

    def instr(self, s):
        if self._u is None:
            return False
        return s.find(unichr(self._u)) != -1

    def __hash__(self):
        return hash(self._u)

    def __eq__(self, other):
        assert isinstance(other, _Char), other
        return self._u == other._u

    def __nonzero__(self):
        return not self._u is None

class Token:
    def __init__(self, tok, atom=None):
        self.tok = tok
        self.atom = atom
        self.start_offset = None
        self.end_offset = None
    def set_offset(self, start_offset, end_offset):
        self.start_offset = start_offset
        self.end_offset = end_offset
    def __repr__(self):
        return 'Token(%r, %r)' % \
            (self.tok, self.atom)

class TokenStream:
    def __init__(self, content, start_offset=0):
        assert isinstance(start_offset, int)
        self._content = content
        self._start_offset = start_offset
        self._offset = 0
        self._watched_offset = None

    def get_offset(self):
        return self._start_offset + self._offset

    def watch_reads(self):
        self._watched_offset = self._offset

    def get_watched_reads(self):
        assert not self._watched_offset == None
        s = self._content[self._watched_offset:self._offset]
        self._watched_offset = None
        return s

    def eof(self):
        return self._offset >= len(self._content)

    def readchr(self):
        c = self.peekchr()
        if not c:
            raise JSSyntaxError(self.get_offset(), 'unexpected_eof')
        self._offset += 1
        return c

    def readchrif(self, expect):
        if self.peekchr() == expect:
            self._offset += 1
            return expect
        return _Char(None)

    def readchrin(self, seq):
        s = self.peekchrin(seq)
        if s:
            self._offset += 1
        return s

    def peekchr(self):
        if self._offset < len(self._content):
            return _Char.fromstr(self._content, self._offset)
        return _Char(None)

    def peekchrin(self, seq):
        c = self.peekchr()
        if c and c.instr(seq):
            return c
        return _Char(None)

    def readtextif(self, text):
        """ Returns the string if found. Otherwise returns None.
        """
        len_ = len(text)
        if self._offset + len_ <= len(self._content):
            peeked = self._content[self._offset:self._offset+len_]
            if peeked == text:
                self._offset += len_
                return text

class Tokenizer:
    def __init__(self, stream):
        self._stream = stream
        self._peeked = []
        self._error = False

    def peek(self):
        self._readahead()
        return self._peeked[-1]

    def peek_sameline(self):
        self._readahead()
        for peek in self._peeked:
            if peek.tok == tok.EOL:
                return peek
        else:
            return peek

    def advance(self):
        assert not self._error

        self._readahead()
        peek = self._peeked[-1]
        self._peeked = []
        if peek.tok == tok.ERROR:
            self._error = True
            raise JSSyntaxError(peek.start_offset, peek.atom or 'syntax_error')
        return peek

    def next_withregexp(self):
        assert not self._error
        self._readahead()
        if self._peeked[-1].tok == tok.DIV:
            token = self._parse_rest_of_regexp()
            token.set_offset(self._peeked[-1].start_offset, self._stream.get_offset()-1)
            self._peeked = []
            if token.tok == tok.ERROR:
                self._error = True
                raise JSSyntaxError(token.start_offset, token.atom or 'syntax_error')
            return token
        else:
            return self.advance()

    def expect(self, tok):
        encountered = self.advance()
        if encountered.tok != tok:
            raise JSSyntaxError(encountered.start_offset, 'expected_tok',
                                { 'token': tok.getliteral() })
        return encountered

    def expect_identifiername(self):
        encountered = self.advance()
        if tok.keywords.has(encountered.tok) != -1:
            encountered.tok = tok.NAME
        if encountered.tok != tok.NAME:
            raise JSSyntaxError(encountered.start_offset, 'syntax_error')
        return encountered

    def _readahead(self):
        """ Always ensure that a valid token is at the end of the queue.
        """
        if self._peeked:
            assert self._peeked[-1].tok not in (tok.EOL, tok.SPACE,
                                                tok.C_COMMENT, tok.CPP_COMMENT,
                                                tok.HTML_COMMENT)
            return
        while True:
            start_offset = self._stream.get_offset()
            peek = self._next()
            end_offset = self._stream.get_offset()-1
            if peek.tok == tok.ERROR:
                peek.set_offset(end_offset, end_offset)
            else:
                peek.set_offset(start_offset, end_offset)

            self._peeked.append(peek)
            assert isinstance(peek.tok, tok.TokenType), repr(peek.tok)
            if peek.tok not in (tok.EOL, tok.SPACE,
                                tok.C_COMMENT, tok.CPP_COMMENT,
                                tok.HTML_COMMENT):
                return

    def _parse_rest_of_regexp(self):
        stream = self._stream
        while True:
            c = stream.readchr()
            if c == _Char.ord('\\'):
                c = stream.readchr()
                if c == _Char.ord('\n'):
                    return Token(tok.ERROR)
            elif c == _Char.ord('['):
                while True:
                    c = stream.readchr()
                    if c == _Char.ord('\n'):
                        return Token(tok.ERROR)
                    elif c == _Char.ord(']'):
                        break
            elif c == _Char.ord('\n'):
                return Token(tok.ERROR)
            elif c == _Char.ord('/'):
                break

        # TODO: Validate and save
        while True:
            c = stream.readchrin(_IDENT)
            if not c:
                break

        return Token(tok.REGEXP)

    def _next(self, parse_regexp=False):
        stream = self._stream

        if stream.eof():
            return Token(tok.EOF)

        stream.watch_reads()

        c = stream.readchr()

        # WHITESPACE
        if c.instr(_WHITESPACE) or c.instr(_LINETERMINATOR):
            linebreak = c.instr(_LINETERMINATOR)
            while True:
                if stream.readchrin(_LINETERMINATOR):
                    linebreak = True
                elif stream.readchrin(_WHITESPACE):
                    pass
                else:
                    break
            if linebreak:
                return Token(tok.EOL)
            else:
                return Token(tok.SPACE)

        # COMMENTS
        if c == _Char.ord('/'):
            if stream.peekchr() == _Char.ord('/'):
                while not stream.eof() and not stream.peekchrin(_LINETERMINATOR):
                    stream.readchr()
                return Token(tok.CPP_COMMENT)
            if stream.peekchr() == _Char.ord('*'):
                linebreak = False
                while True:
                    if stream.eof():
                        return Token(tok.ERROR, atom='unterminated_comment')
                    c = stream.readchr()
                    if c.instr(_LINETERMINATOR):
                        linebreak = True
                    elif c == _Char.ord('*') and stream.readchrif(_Char.ord('/')):
                        return Token(tok.C_COMMENT)
                return Token(tok.EOF)
        elif c == _Char.ord('<'):
            if stream.readtextif('!--'):
                while not stream.eof() and not stream.peekchrin(_LINETERMINATOR):
                    stream.readchr()
                return Token(tok.HTML_COMMENT)

        # STRING LITERALS
        if c == _Char.ord('"') or c == _Char.ord("'"):
            # TODO: Decode
            s = ''
            quote = c
            while True:
                c = stream.readchr()
                if c == _Char.ord('\\'):
                    c = stream.readchr()
                elif c == quote:
                    return Token(tok.STRING, atom=s)
                s += c.tostr()

        # NUMBERS
        if c.instr(_DIGITS) or (c == _Char.ord('.') and stream.peekchrin(_DIGITS)):
            s = c # TODO
            if c == _Char.ord('0') and stream.readchrin('xX'):
                # Hex
                while stream.readchrin(_HEX_DIGITS):
                    pass
            elif c == _Char.ord('0') and stream.readchrin(_DIGITS):
                # Octal
                while stream.readchrin(_DIGITS):
                    pass
            else:
                # Decimal
                if c != '.':
                    while stream.readchrin(_DIGITS):
                        pass
                    stream.readchrif(_Char.ord('.'))

                while stream.readchrin(_DIGITS):
                    pass

                if stream.readchrin('eE'):
                    stream.readchrin('+-')
                    if not stream.readchrin(_DIGITS):
                        raise JSSyntaxError(stream.get_offset(), 'syntax_error')
                    while stream.readchrin(_DIGITS):
                        pass

                if stream.peekchrin(_IDENT):
                    return Token(tok.ERROR)

            atom = stream.get_watched_reads()
            return Token(tok.NUMBER, atom=atom)

        if tok.punctuators.hasprefix(c.tostr()):
            s = c.tostr()
            while True:
                c = stream.peekchr()
                if c and tok.punctuators.hasprefix(s + c.tostr()):
                    s += c.tostr()
                    stream.readchr()
                else:
                    break
            d = tok.punctuators.get(s)
            if not d:
                raise JSSyntaxError(stream.get_offset(), 'syntax_error')
            return Token(d)
        if c.instr(_IDENT):
            while stream.readchrin(_IDENT + _DIGITS):
                pass

            atom = stream.get_watched_reads()
            tt = tok.keywords.get(atom, tok.NAME)
            t = Token(tt)
            t.atom = atom
            return t

        raise JSSyntaxError(stream.get_offset(), 'unexpected_char',
                            { 'char': c.tostr() })
