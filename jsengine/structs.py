# vim: ts=4 sw=4 expandtab
import bisect
import functools

from parser._constants_kind import kind
from parser._constants_op import op

class NodePositions:
    " Given a string, allows [x] lookups for NodePos line and column numbers."
    def __init__(self, text, start_pos=None):
        # Find the length of each line and incrementally sum all of the lengths
        # to determine the ending position of each line.
        self._start_pos = start_pos
        self._lines = text.splitlines(True)
        lines = [0] + [len(x) for x in self._lines]
        for x in range(1, len(lines)):
            lines[x] += lines[x-1]
        self._line_offsets = lines
    def from_offset(self, offset):
        line = bisect.bisect(self._line_offsets, offset)-1
        col = offset - self._line_offsets[line]
        if self._start_pos:
            if line == 0:
                col += self._start_pos.col
            line += self._start_pos.line
        return NodePos(line, col)
    def to_offset(self, pos):
        pos = self._to_rel_pos(pos)
        offset = self._line_offsets[pos.line] + pos.col
        assert offset <= self._line_offsets[pos.line+1] # out-of-bounds col num
        return offset
    def text(self, start, end):
        assert start <= end
        start, end = self._to_rel_pos(start), self._to_rel_pos(end)
        # Trim the ending first in case it's a single line.
        lines = self._lines[start.line:end.line+1]
        lines[-1] = lines[-1][:end.col+1]
        lines[0] = lines[0][start.col:]
        return ''.join(lines)
    def _to_rel_pos(self, pos):
        " converts a position to a position relative to self._start_pos "
        if not self._start_pos:
            return pos
        line, col = pos.line, pos.col
        line -= self._start_pos.line
        if line == 0:
            col -= self._start_pos.col
        assert line >= 0 and col >= 0 # out-of-bounds node position
        return NodePos(line, col)

class NodeRanges:
    def __init__(self):
        self._offsets = []
    def add(self, start, end):
        i = bisect.bisect_left(self._offsets, start)
        if i % 2 == 1:
            i -= 1
            start = self._offsets[i]

        end = end + 1
        j = bisect.bisect_left(self._offsets, end)
        if j % 2 == 1:
            end = self._offsets[j]
            j += 1

        self._offsets[i:j] = [start,end]
    def has(self, pos):
        return bisect.bisect_right(self._offsets, pos) % 2 == 1

@functools.total_ordering
class NodePos:
    def __init__(self, line, col):
        self.line = line
        self.col = col

    def __repr__(self):
        return 'NodePos(%i, %i)' % (self.line, self.col)

    def __unicode__(self):
        return '(line %i, col %i)' % \
            (self.line + 1, self.col + 1)

    def __lt__(self, other):
        return self.line < other.line or \
            (self.line == other.line and self.col < other.col)

    def __eq__(self, other):
        return self.line == other.line and self.col == other.col

class ParseNode:
    node_index = None
    parent = None
    def __init__(self, kind_, op_, start_pos, end_pos, atom, kids,
                 no_semi=False, end_comma=None, fn_args=None):
        assert not kids is None
        assert kind.contains(kind_)
        assert op_ is None or op.contains(op_)
        if kind_ == kind.RESERVED:
            assert start_pos is None
            assert end_pos is None
        else:
            assert isinstance(start_pos, NodePos), repr(start_pos)
            assert isinstance(end_pos, NodePos), repr(end_pos)
        assert end_comma is None or isinstance(end_comma, ParseNode)
        assert (start_pos is None and end_pos is None) or start_pos <= end_pos
        self.kind = kind_
        self.opcode = op_
        self.atom = atom
        self.kids = kids
        self._lefthandside = False
        self.startpos = start_pos
        self.endpos = end_pos
        self.no_semi = no_semi
        self.end_comma = end_comma
        
        for i, kid in enumerate(self.kids):
            if kid:
                assert isinstance(kid, ParseNode)
                kid.node_index = i
                kid.parent = self
        if kind_ == kind.FUNCTION: #TODO
            self.fn_name = self.atom
            assert not fn_args is None
            self.fn_args = fn_args
        else:
            assert fn_args is None
        if self.kind == kind.NUMBER:
            if self.atom.lower().startswith('0x'):
               self.dval = int(self.atom, 16)
            elif self.atom.startswith('0') and self.atom.isdigit():
               self.dval = int(self.atom, 8)
            else:
               self.dval = float(self.atom)

    def start_pos(self):
        return self.startpos
    def end_pos(self):
        return self.endpos

    def is_equivalent(self, other, are_functions_equiv=False):
        if not other:
            return False

        # Deal with nested parentheses
        if self.kind == kind.RP:
            return self.kids[0].is_equivalent(other, are_functions_equiv)
        while other.kind == kind.RP:
            other, = other.kids

        op_conversion = {
            op.SETNAME: op.NAME,
            op.SETPROP: op.GETPROP,
            op.SETELEM: op.GETELEM,
            op.SETCALL: op.CALL,
        }
        self_opcode = op_conversion.get(self.opcode, self.opcode)
        other_opcode = op_conversion.get(other.opcode, other.opcode)

        # Bail out for functions
        if not are_functions_equiv:
            if self.kind == kind.FUNCTION:
                return False
            if self.kind == kind.LP and self_opcode == op.CALL:
                return False

        if self.kind == kind.DOT and self_opcode == op.GETPROP and \
            other.kind == kind.LB and other_opcode == op.GETELEM and \
            self.atom == other.kids[1].atom and \
            self.kids[0].is_equivalent(other.kids[0], are_functions_equiv):
            return True
        if other.kind == kind.DOT and other_opcode == op.GETPROP and \
            self.kind == kind.LB and self_opcode == op.GETELEM and \
            self.kids[1].atom == other.atom and \
            self.kids[0].is_equivalent(other.kids[0], are_functions_equiv):
            return True

        if self.kind != other.kind:
            return False
        if self_opcode != other_opcode:
            return False

        # Check atoms on names, properties, and string constants
        if self.kind in (kind.NAME, kind.DOT, kind.STRING) and self.atom != other.atom:
            return False

        # Check values on numbers
        if self.kind == kind.NUMBER and self.dval != other.dval:
            return False

        # Compare child nodes
        if len(self.kids) != len(other.kids):
            return False
        for i in range(0, len(self.kids)):
            # Watch for dead nodes
            if not self.kids[i]:
                if not other.kids[i]: return True
                else: return False
            if not self.kids[i].is_equivalent(other.kids[i]):
                return False

        return True
