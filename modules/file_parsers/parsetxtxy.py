#!/usr/bin/env python3
#command line options for parse-text: in out format
import sys
import json
import textparsers as tp
import metadatatools as mdt


format = sys.argv[3]
infilename = sys.argv[1]
outfilename = sys.argv[2]
if (format == "txtXY"):
	data = tp.parseTxtXY(infilename)
	tp.saveSampleFile(outfilename, data['data'], data['metadata'])
	print(json.dumps(mdt.getCollectionInfo(outfilename), indent=2, ensure_ascii=False, skipkeys=True))
else:
	print('Unsupported type', file=sys.stderr)
