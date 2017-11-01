#!/usr/bin/env python3
#command line options for parse-text: in out format
import sys
import textparsers as tp

infilename = sys.argv[1]
outfilename = sys.argv[2]
print(infilename)
print(outfilename)
data = tp.parseTxtXY(infilename)
tp.saveSampleFile(outfilename, data['data'], data['metadata'])
sys.exit()

