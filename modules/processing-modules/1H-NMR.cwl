cwlVersion: cwl:draft-3
class: CommandLineTool
id: 1HNMR
label: 1H-NMR
baseCommand: [parsetxtxy.py]
inputs:
  - id: inputFile
    type: File
    inputBinding:
      position: 1
  - id: frequency
    type: double
    inputBinding:
      position: 1
      value: 599733800.0
requirements:
  - class: DockerRequirement
    dockerPull: 'wsubirg/omics-dashboard:text-parser'
