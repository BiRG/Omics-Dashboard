class: CommandLineTool
cwlVersion: v1.0
id: parsetxtxy
baseCommand:
  - batchparsetxtxy.py
inputs:
  - id: inputFile
    type: File
    inputBinding:
      position: 0
  - id: prefix
    type: string
    inputBinding:
      position: 1
outputs:
  - id: output
    type: File
    outputBinding:
      glob: '*.h5'
label: txtXY
