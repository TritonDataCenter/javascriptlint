# vim: sw=4 ts=4 et
from jsengine import JSSyntaxError
import tok

_WHITESPACE = u'\u0020\t\u000B\u000C\u00A0\uFFFF'
_LINETERMINATOR = u'\u000A\u000D\u2028\u2029'
_DIGITS = u'0123456789'
_DOT_DIGITS = [u'.%s' % digit for digit in _DIGITS]
_HEX_DIGITS = _DIGITS + u'abcdefABCDEF'
_IDENT = u'abcdefghijklmnopqrstuvwxyz' + \
         u'ABCDEFGHIJKLMNOPQRSTUVWXYZ' + \
         u'$_'

_KEYWORDS = tok.getkeywords()
_PUNCTUATOR_TREE = tok.get_punctuator_tree()

def _str_has_chr(s, c):
    assert len(c) <= 1
    return c in s

def _chr_to_str(c):
    assert len(c) <= 1
    return c

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
        return ''

    def readchrin(self, seq):
        s = self.peekchrin(seq)
        if s:
            self._offset += 1
        return s

    def peekchr(self):
        if self._offset < len(self._content):
            return self._content[self._offset]
        return ''

    def peekchrin(self, seq):
        c = self.peekchr()
        if c and _str_has_chr(seq, c):
            return c
        return ''

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
                raise JSSyntaxError(peek.start_offset, peek.atom or 'syntax_error')
            return token
        else:
            return self.advance()

    def expect(self, tok):
        encountered = self.advance()
        if encountered.tok != tok:
            raise JSSyntaxError(encountered.start_offset, 'expected_tok',
                                { 'token': tok })
        return encountered

    def expect_identifiername(self):
        encountered = self.advance()
        if encountered.tok in list(_KEYWORDS.values()):
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
            if c == '\\':
                c = stream.readchr()
                if c == '\n':
                    return Token(tok.ERROR)
            elif c == '[':
                while True:
                    c = stream.readchr()
                    if c == '\n':
                        return Token(tok.ERROR)
                    elif c == ']':
                        break
            elif c == '\n':
                return Token(tok.ERROR)
            elif c == '/':
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
        if _str_has_chr(_WHITESPACE, c) or _str_has_chr(_LINETERMINATOR, c):
            linebreak = _str_has_chr(_LINETERMINATOR, c)
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
        if c == '/':
            if stream.peekchr() == '/':
                while not stream.eof() and not stream.peekchrin(_LINETERMINATOR):
                    stream.readchr()
                return Token(tok.CPP_COMMENT)
            if stream.peekchr() == '*':
                linebreak = False
                while True:
                    if stream.eof():
                        return Token(tok.ERROR, atom='unterminated_comment')
                    c = stream.readchr()
                    if _str_has_chr(_LINETERMINATOR, c):
                        linebreak = True
                    elif c == '*' and stream.readchrif('/'):
                        return Token(tok.C_COMMENT)
                return Token(tok.EOF)
        elif c == '<':
            if stream.readtextif('!--'):
                while not stream.eof() and not stream.peekchrin(_LINETERMINATOR):
                    stream.readchr()
                return Token(tok.HTML_COMMENT)

        # STRING LITERALS
        if c == '"' or c == "'":
            # TODO: Decode
            s = ''
            quote = c
            while True:
                c = stream.readchr()
                if c == '\\':
                    c = stream.readchr()
                elif c == quote:
                    return Token(tok.STRING, atom=s)
                s += _chr_to_str(c)

        # NUMBERS
        if _str_has_chr(_DIGITS, c) or (c == '.' and stream.peekchrin(_DIGITS)):
            s = c # TODO
            if c == '0' and stream.readchrin('xX'):
                # Hex
                while stream.readchrin(_HEX_DIGITS):
                    pass
            elif c == '0' and stream.readchrin(_DIGITS):
                # Octal
                while stream.readchrin(_DIGITS):
                    pass
            else:
                # Decimal
                if c != '.':
                    while stream.readchrin(_DIGITS):
                        pass
                    stream.readchrif('.')

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

        if c in _PUNCTUATOR_TREE:
            d = _PUNCTUATOR_TREE[c]
            while True:
                c = stream.readchrin(u''.join(d.keys()))
                if c:
                    d = d[c]
                else:
                    break
            try:
                return Token(d[''])
            except KeyError:
                print('oops')
                raise JSSyntaxError(stream.get_offset(), 'syntax_error')

        if _str_has_chr(_IDENT, c):
            while stream.readchrin(_IDENT + _DIGITS):
                pass

            atom = stream.get_watched_reads()
            if atom in _KEYWORDS:
                return Token(_KEYWORDS[atom], atom=atom)
            return Token(tok.NAME, atom=atom)

        raise JSSyntaxError(stream.get_offset(), 'unexpected_char',
                            { 'char': _chr_to_str(c) })
