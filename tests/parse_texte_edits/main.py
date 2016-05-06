#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import glob
import os
import subprocess
import codecs

# http://eli.thegreenplace.net/2014/04/02/dynamically-generating-python-test-cases
class TestTexteEditsParser(unittest.TestCase):
    longMessage = True

def get_compare_outputs_fn(description, input_filename, output_filename):
    def test(self):
        process = subprocess.Popen(
            'python ../../scripts/collectdata/parse_texte_edits.py ' + input_filename,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        out, err = process.communicate()
        out = out.decode('utf-8')

        output_data = codecs.open(output_filename, 'r', 'utf-8').read()
        self.assertMultiLineEqual(out, output_data, description)
    return test

if __name__ == '__main__':
    inputs = glob.glob('input/*.json')

    for input_filename in inputs:
        description = os.path.splitext(os.path.basename(input_filename))[0]
        output_filename = './output/' + os.path.basename(input_filename)
        if os.path.isfile(output_filename):
            test_func = get_compare_outputs_fn(description, input_filename, output_filename)
            setattr(TestTexteEditsParser, 'test_{0}'.format(description), test_func)

    unittest.main()
