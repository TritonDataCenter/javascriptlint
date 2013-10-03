#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
import os
import re
import sys

import pylint.lint
from pylint.reporters.text import TextReporter

import javascriptlint.conf
import javascriptlint.lint

_DEFAULT_CONF = """
# This warning triggers a lot of warnings in many of the tests, so only enable
# it when specifically testing it.
-unreferenced_argument
-unreferenced_function
-unreferenced_variable
"""

class TestError(Exception):
    pass

def _get_conf(script):
    regexp = re.compile(r"/\*conf:([^*]*)\*/")
    text = '\n'.join(regexp.findall(script))
    conf = javascriptlint.conf.Conf()
    conf.loadtext(_DEFAULT_CONF)
    conf.loadtext(text)
    return conf

def _get_expected_warnings(script):
    "returns an array of tuples -- line, warning"
    warnings = []

    regexp = re.compile(r"/\*warning:([^*]*)\*/")

    lines = script.splitlines()
    for i in range(0, len(lines)):
        for warning in regexp.findall(lines[i]):
            # TODO: implement these
            unimpl_warnings = ('dup_option_explicit',)
            if not warning in unimpl_warnings:
                warnings.append((i, warning))
    return warnings

def _testfile(path):
    # Parse the script and find the expected warnings.
    script = open(path).read()
    expected_warnings = _get_expected_warnings(script)
    unexpected_warnings = []
    conf = _get_conf(script)

    def lint_error(path, line, col, errname, errdesc):
        warning = (line, errname)

        # Bad hack to fix line numbers on ambiguous else statements
        # TODO: Fix tests.
        if errname == 'ambiguous_else_stmt' and not warning in expected_warnings:
            warning = (line-1, errname)

        if warning in expected_warnings:
            expected_warnings.remove(warning)
        else:
            unexpected_warnings.append(warning + (errdesc,))

    javascriptlint.lint.lint_files([path], lint_error, 'utf-8', conf=conf)

    errors = []
    if expected_warnings:
        errors.append('Expected warnings:')
        for line, warning in expected_warnings:
            errors.append('\tline %i: %s' % (line+1, warning))
    if unexpected_warnings:
        errors.append('Unexpected warnings:')
        for line, warning, errdesc in unexpected_warnings:
            errors.append('\tline %i: %s/%s' % (line+1, warning, errdesc))
    if errors:
        raise TestError('\n'.join(errors))

def _get_test_files():
    # Get a list of test files.
    dir_ = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')

    all_files = []
    for root, dirs, files in os.walk(dir_):
        all_files += [os.path.join(dir_, root, file) for file in files]
        if '.svn' in dirs:
            dirs.remove('.svn')
        # TODO
        if 'conf' in dirs:
            dirs.remove('conf')
    all_files.sort()
    return all_files

class _CustomLintReporter(TextReporter):
    line_format = '{path}({line}): [{msg_id}({symbol}){obj}] {msg}'
    def __init__(self):
        TextReporter.__init__(self)
        self.msg_count = 0

    def write_message(self, msg):
        TextReporter.write_message(self, msg)
        self.msg_count += 1

def _get_python_modules(dir_):
    for root, dirs, files in os.walk(dir_):
        for exclude in ('build', 'dist'):
            if exclude in dirs:
                build.remove(exclude)

        if '.svn' in dirs:
            dirs.remove('.svn')
        for name in files:
            if name.endswith('.py'):
                yield os.path.join(root, name)

def _run_pylint():
    IGNORE = [
        'C0111', # Missing docstring
        'I0011', # Locally disabling warning
        'R0902', # Too many instance attributes (%s/%s)
        'R0903', # Too few public methods (%s/%s)
        'R0904', # Too many public methods (%s/%s)
        'R0911', # Too many return statements (%s/%s)
        'R0912', # Too many branches (%s/%s)
        'R0913', # Too many arguments (%s/%s)
        'R0914', # Too many local variables (%s/%s)
        'R0915', # Too many statements (%s/%s)
        'W0142', # Used * or ** magic
    ]
    REVIEW = [
        'C0103', # Invalid name "%s" (should match %s)
        'C0202', # Class method should have "cls" as first argument
        'C0301', # Line too long (%s/%s)
        'C0321', # More than one statement on a single line
        'C1001', # Old style class
        'E0602', # Undefined variable %r
        'E1101', # %s %r has no %r member
        'E1103', # %s %r has no %r member (but some types could not be inferred)
        'E1306', # Not enough arguments for format string
        'F0401', # Cyclic import (%s)
        'R0201', # Attribute %r defined outside __init__
        'R0924', # Badly implemented
        'W0109', # Duplicate key %r in dictionary
        'W0120', # Else clause on loop without a break statement
        'W0141', # Used builtin function %r
        'W0201', # Attribute %r defined outside __init__
        'W0212', # Access to a protected member %s of a client class
        'W0231', # __init__ method from base class %r is not called
        'W0232', # Class has no __init__ method
        'W0301', # Unnecessary semicolon
        'W0311', # Bad indentation
        'W0401', # Wildcard import %s
        'W0403', # Relative import %r
        'W0511', # TODO
        'W0611', # Unused import %s
        'W0612', # unused variable
        'W0613', # Unused argument %r
        'W0614', # Unused import %s from wildcard import
        'W0621', # Redefining name %r from outer scope (line %s)
        'W0622', # Redefining built-in %r
        'W0631', # Using possibly undefined loop variable %r
        'W0632', # unbalanced-tuple-unpacking
        'W1401', # Anomalous backslash in string
    ]

    dir_ = os.path.dirname(os.path.abspath(__file__))
    modules = list(_get_python_modules(dir_))
    reporter = _CustomLintReporter()
    pylint.lint.Run([
        '--reports=n',
    ] + [
        '--disable=%s' % code for code in (IGNORE + REVIEW)
    ] + modules, reporter=reporter, exit=False)
    if reporter.msg_count:
        print '\nLint failed!\n'
        sys.exit(1)

def main():
    # _run_pylint()

    haderrors = False
    for file in _get_test_files():
        ext = os.path.splitext(file)[1]
        if ext in ('.htm', '.html', '.js'):
            try:
                _testfile(file)
            except TestError, error:
                haderrors = True
                print error

    if haderrors:
        print '\nOne or more tests failed!'
    else:
        print '\nAll tests passed successfully.'
    sys.exit(haderrors)

if __name__  == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write('\n\nCanceled.\n')
        sys.exit(1)

