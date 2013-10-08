#!/usr/bin/env python
# vim: ts=4 sw=4 expandtab
""" Parses a script into nodes. """
import re
import unittest

import jsengine.parser
from jsengine.parser import kind as tok
from jsengine.parser import op
from jsengine.structs import *

from .util import JSVersion

def isvalidversion(jsversion):
    if jsversion is None:
        return True
    return jsengine.parser.is_valid_version(jsversion.version)

def findpossiblecomments(script, script_offset):
    assert not script_offset is None
    pos = 0
    single_line_re = r"//[^\r\n]*"
    multi_line_re = r"/\*(.*?)\*/"
    full_re = "(%s)|(%s)" % (single_line_re, multi_line_re)
    comment_re = re.compile(full_re, re.DOTALL)

    comments = []
    while True:
        match = comment_re.search(script, pos)
        if not match:
            return comments

        # Get the comment text
        comment_text = script[match.start():match.end()]
        if comment_text.startswith('/*'):
            comment_text = comment_text[2:-2]
            opcode = op.C_COMMENT
        else:
            comment_text = comment_text[2:]
            opcode = op.CPP_COMMENT

        start_offset = match.start()
        end_offset = match.end()-1

        comment_node = ParseNode(kind.COMMENT, opcode,
                                 script_offset + start_offset,
                                 script_offset + end_offset, comment_text, [])
        comments.append(comment_node)

        # Start searching immediately after the start of the comment in case
        # this one was within a string or a regexp.
        pos = match.start()+1

def parse(script, jsversion, error_callback, start_offset=0):
    """ All node positions will be relative to start_offset. This allows
        scripts to be embedded in a file (for example, HTML).
    """
    assert not start_offset is None
    jsversion = jsversion or JSVersion.default()
    assert isvalidversion(jsversion), jsversion
    if jsversion.e4x:
        error_callback(start_offset, 'e4x_deprecated', {})
    return jsengine.parser.parse(script, jsversion.version,
                                 error_callback, start_offset)

def filtercomments(possible_comments, root_node):
    comment_ignore_ranges = NodeRanges()

    def process(node):
        if node.kind == tok.STRING or \
                (node.kind == tok.OBJECT and node.opcode == op.REGEXP):
            comment_ignore_ranges.add(node.start_offset, node.end_offset)
        for kid in node.kids:
            if kid:
                process(kid)
    process(root_node)

    comments = []
    for comment in possible_comments:
        if comment_ignore_ranges.has(comment.start_offset):
            continue
        comment_ignore_ranges.add(comment.start_offset, comment.end_offset)
        comments.append(comment)
    return comments

def findcomments(script, root_node, start_offset=0):
    possible_comments = findpossiblecomments(script, start_offset)
    return filtercomments(possible_comments, root_node)

def is_compilable_unit(script, jsversion):
    jsversion = jsversion or JSVersion.default()
    assert isvalidversion(jsversion)
    return jsengine.parser.is_compilable_unit(script, jsversion.version)

def _dump_node(node, node_positions, depth=0):
    if node is None:
        print '     '*depth,
        print '(None)'
        print
    else:
        print '     '*depth,
        print '%s, %s' % (repr(node.kind), repr(node.opcode))
        print '     '*depth,
        print '%s - %s' % (node_positions.from_offset(node.start_offset),
                           node_positions.from_offset(node.end_offset))
        if hasattr(node, 'atom'):
            print '     '*depth,
            print 'atom: %s' % node.atom
        if node.no_semi:
            print '     '*depth,
            print '(no semicolon)'
        print
        for node in node.kids:
            _dump_node(node, node_positions, depth+1)

def dump_tree(script):
    def error_callback(line, col, msg, msg_args):
        print '(%i, %i): %s', (line, col, msg)
    node = parse(script, None, error_callback)
    node_positions = NodePositions(script)
    _dump_node(node, node_positions)

class TestComments(unittest.TestCase):
    def _test(self, script, expected_comments):
        root = parse(script, None, lambda line, col, msg: None)
        comments = findcomments(script, root)
        encountered_comments = [node.atom for node in comments]
        self.assertEquals(encountered_comments, list(expected_comments))
    def testSimpleComments(self):
        self._test('re = /\//g', ())
        self._test('re = /\///g', ())
        self._test('re = /\////g', ('g',))
    def testCComments(self):
        self._test('/*a*//*b*/', ('a', 'b'))
        self._test('/*a\r\na*//*b\r\nb*/', ('a\r\na', 'b\r\nb'))
        self._test('a//*b*/c', ('*b*/c',))
        self._test('a///*b*/c', ('/*b*/c',))
        self._test('a/*//*/;', ('//',))
        self._test('a/*b*/+/*c*/d', ('b', 'c'))

class TestNodePositions(unittest.TestCase):
    def _test(self, text, expected_lines, expected_cols):
        # Get a NodePos list
        positions = NodePositions(text)
        positions = [positions.from_offset(i) for i in range(0, len(text))]
        encountered_lines = ''.join([str(x.line) for x in positions])
        encountered_cols = ''.join([str(x.col) for x in positions])
        self.assertEquals(encountered_lines, expected_lines.replace(' ', ''))
        self.assertEquals(encountered_cols, expected_cols.replace(' ', ''))
    def testSimple(self):
        self._test(
            'abc\r\ndef\nghi\n\nj',
            '0000 0 1111 2222 3 4',
            '0123 4 0123 0123 0 0'
        )
        self._test(
            '\rabc',
            '0 111',
            '0 012'
        )
    def testText(self):
        pos = NodePositions('abc\r\ndef\n\nghi')
        self.assertEquals(pos.text(NodePos(0, 0), NodePos(0, 0)), 'a')
        self.assertEquals(pos.text(NodePos(0, 0), NodePos(0, 2)), 'abc')
        self.assertEquals(pos.text(NodePos(0, 2), NodePos(1, 2)), 'c\r\ndef')
    def testOffset(self):
        pos = NodePositions('abc\r\ndef\n\nghi')
        self.assertEquals(pos.to_offset(NodePos(0, 2)), 2)
        self.assertEquals(pos.to_offset(NodePos(1, 0)), 5)
        self.assertEquals(pos.to_offset(NodePos(3, 1)), 11)
    def testStartPos(self):
        pos = NodePositions('abc\r\ndef\n\nghi', NodePos(3, 4))
        self.assertEquals(pos.to_offset(NodePos(3, 4)), 0)
        self.assertEquals(pos.to_offset(NodePos(3, 5)), 1)
        self.assertEquals(pos.from_offset(0), NodePos(3, 4))
        self.assertEquals(pos.text(NodePos(3, 4), NodePos(3, 4)), 'a')
        self.assertEquals(pos.text(NodePos(3, 4), NodePos(3, 6)), 'abc')
        self.assertEquals(pos.text(NodePos(3, 6), NodePos(4, 2)), 'c\r\ndef')

class TestNodeRanges(unittest.TestCase):
    def testAdd(self):
        r = NodeRanges()
        r.add(5, 10)
        self.assertEquals(r._offsets, [5, 11])
        r.add(15, 20)
        self.assertEquals(r._offsets, [5, 11, 15, 21])
        r.add(21, 22)
        self.assertEquals(r._offsets, [5, 11, 15, 23])
        r.add(4, 5)
        self.assertEquals(r._offsets, [4, 11, 15, 23])
        r.add(9, 11)
        self.assertEquals(r._offsets, [4, 12, 15, 23])
        r.add(10, 20)
        self.assertEquals(r._offsets, [4, 23])
        r.add(4, 22)
        self.assertEquals(r._offsets, [4, 23])
        r.add(30, 30)
        self.assertEquals(r._offsets, [4, 23, 30, 31])
    def testHas(self):
        r = NodeRanges()
        r.add(5, 10)
        r.add(15, 15)
        assert not r.has(4)
        assert r.has(5)
        assert r.has(6)
        assert r.has(9)
        assert r.has(10)
        assert not r.has(14)
        assert r.has(15)
        assert not r.has(16)

class TestCompilableUnit(unittest.TestCase):
    def test(self):
        tests = (
            ('var s = "', False),
            ('bogon()', True),
            ('int syntax_error;', True),
            ('a /* b', False),
            ('re = /.*', False),
            ('{ // missing curly', False)
        )
        for text, expected in tests:
            encountered = is_compilable_unit(text, JSVersion.default())
            self.assertEquals(encountered, expected)
        self.assert_(not is_compilable_unit("/* test", JSVersion.default()))

class TestLineOffset(unittest.TestCase):
    def testErrorPos(self):
        def geterror(script, start_offset):
            errors = []
            def onerror(offset, msg, msg_args):
                errors.append((offset, msg, msg_args))
            parse(script, None, onerror, start_offset)
            self.assertEquals(len(errors), 1)
            return errors[0]
        self.assertEquals(geterror(' ?', 0), (1, 'syntax_error', {}))
        self.assertEquals(geterror('\n ?', 0), (2, 'syntax_error', {}))
        self.assertEquals(geterror(' ?', 2), (3, 'syntax_error', {}))
        self.assertEquals(geterror('\n ?', 2), (4, 'syntax_error', {}))
    def testNodePos(self):
        def getnodepos(script, start_offset):
            root = parse(script, None, None, start_offset)
            self.assertEquals(root.kind, tok.LC)
            var, = root.kids
            self.assertEquals(var.kind, tok.VAR)
            return var.start_offset
        self.assertEquals(getnodepos('var x;', 0), 0)
        self.assertEquals(getnodepos(' var x;', 0), 1)
        self.assertEquals(getnodepos('\n\n var x;', 0), 3)
        self.assertEquals(getnodepos('var x;', 7), 7)
        self.assertEquals(getnodepos(' var x;', 7), 8)
        self.assertEquals(getnodepos('\n\n var x;', 7), 10)
    def testComments(self):
        def testcomment(comment, startpos, expected_offset):
            root = parse(comment, None, None, startpos)
            comment, = findcomments(comment, root, startpos)
            self.assertEquals(comment.start_offset, expected_offset)
        for comment in ('/*comment*/', '//comment'):
            testcomment(comment, 0, 0)
            testcomment(' %s' % comment, 0, 1)
            testcomment('\n\n %s' % comment, 0, 3)
            testcomment('%s' % comment, 7, 7)
            testcomment(' %s' % comment, 7, 8)
            testcomment('\n\n %s' % comment, 7, 10)

if __name__ == '__main__':
    unittest.main()

