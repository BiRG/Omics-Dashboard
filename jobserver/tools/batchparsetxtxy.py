#!/usr/bin/env python3
import sys
import textparsers as tp
import os
infilenames = sys.argv[1:len(sys.argv)-1]
nameprefix = sys.argv[len(sys.argv)-1]
for infilename in infilenames:
    outfilename = f'{os.environ["HOME"]}/{os.path.basename(infilename)}.h5'
    data = tp.parseTxtXY(infilename)
    data['metadata']['name'] = f'{nameprefix}: {os.path.basename(infilename)}'
    tp.saveSampleFile(outfilename, data['data'], data['metadata'])
sys.exit(0)
