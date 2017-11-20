#!/usr/bin/env python3
import sys
import textparsers as tp
import os

infilename = sys.argv[1]
outfilename = os.path.basename(infilename) + '.h5'
print(infilename)
print(outfilename)
data = tp.parseTxtXY(infilename)
tp.saveSampleFile(outfilename, data['data'], data['metadata'])
sys.exit(0)
