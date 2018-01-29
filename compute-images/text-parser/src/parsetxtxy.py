#!/usr/bin/env python3
import sys
import textparsers as tp
import os

infilename = sys.argv[1]
outfilename = f'{os.environ["HOME"]}/{os.path.basename(infilename)}.h5'
data = tp.parseTxtXY(infilename)
tp.saveSampleFile(outfilename, data['data'], data['metadata'])
sys.exit(0)
