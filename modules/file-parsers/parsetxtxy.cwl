class: CommandLineTool
cwlVersion: v1.0
id: parsetxtxy
baseCommand:
  - parsetxtxy.py
inputs:
  - id: inputFile
    type: File
    inputBinding:
      position: 0
outputs:
  - id: output
    type: File
    outputBinding:
      glob: '*.h5'
label: txtXY
requirements:
  - class: DockerRequirement
    dockerPull: 'wsubirg/omics-dashboard:text-parser'