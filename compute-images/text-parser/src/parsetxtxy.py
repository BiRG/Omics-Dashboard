#!/usr/bin/env python3
#command line options for parse-text: in out format
import sys
import json
import textparsers as tp

infilename = sys.argv[1]
outfilename = sys.argv[2]
data = tp.parseTxtXY(infilename)
tp.saveSampleFile(outfilename, data['data'], data['metadata'])
