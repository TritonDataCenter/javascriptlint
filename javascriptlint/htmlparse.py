# vim: ts=4 sw=4 expandtab
import HTMLParser
import unittest

from jsengine.structs import NodePos, NodePositions

class _Parser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self._tags = []
        self._node_positions = None

    def feed(self, data):
        # Reset line numbers whenever we get data.
        self._node_positions = None
        HTMLParser.HTMLParser.feed(self, data)

    def handle_starttag(self, tag, attributes):
        if tag.lower() == 'script':
            attr = dict(attributes)
            self._tags.append({
                'type': 'start',
                'offset': self._getoffset(),
                'len': len(self.get_starttag_text()),
                'attr': attr
            })

    def handle_endtag(self, tag):
        if tag.lower() == 'script':
            self._tags.append({
                'type': 'end',
                'offset': self._getoffset(),
            })

    def unknown_decl(self, data):
        # Ignore unknown declarations instead of raising an exception.
        pass

    def gettags(self):
        return self._tags

    def _getoffset(self):
        # htmlparse returns 1-based line numbers. Calculate the offset of the
        # script's contents.
        if self._node_positions is None:
            self._node_positions = NodePositions(self.rawdata)
        pos = NodePos(self.lineno - 1, self.offset)
        return self._node_positions.to_offset(pos)


def findscripttags(s):
    parser = _Parser()
    parser.feed(s)
    parser.close()
    return parser.gettags()

class TestHTMLParse(unittest.TestCase):
    def testConditionalComments(self):
        html = """
<!--[if IE]>This is Internet Explorer.<![endif]-->
<![if !IE]>This is not Internet Explorer<![endif]>
"""
        findscripttags(html)

