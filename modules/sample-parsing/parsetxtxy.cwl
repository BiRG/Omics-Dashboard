class: CommandLineTool
cwlVersion: v1.0
id: parsetxtxy
baseCommand:
  - batchparsetxtxy.py
inputs:
  - id: inputFiles
    doc: Text files containing data.
    type: File[]
    inputBinding:
      position: 0
  - id: prefix
    doc: A prefix applied to the "name" field of all files.
    type: string
    inputBinding:
      position: 1
outputs:
  - id: outputFiles
    doc: HDF5 files containing the parsed files.
    type: File[]
    outputBinding:
      glob: '*.h5'
label: txtXY
doc: Parse a text file in the .txtXY format, which consists of a number of header lines with $key:value pairs followed by paired numeric data.
