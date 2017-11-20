cwlVersion: cwl:draft-3
class: CommandLineTool
id: parsetxtxy
label: parsetxtxy
baseCommand: [parsetxtxy.py]
inputs:
  - id: inputFile
    type: File
    inputBinding:
      position: 1
outputs:
  - id: outputFile
    type: File
    outputBinding:
      glob: "*.h5"
requirements:
  - class: DockerRequirement
    dockerPull: 'wsubirg/omics-dashboard:text-parser'