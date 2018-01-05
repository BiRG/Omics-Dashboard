cwlVersion: cwl:draft-3
class: CommandLineTool
id: 13CNMR
label: 13C-NMR
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
      value: 150819500.0
requirements:
  - class: DockerRequirement
    dockerPull: 'wsubirg/omics-dashboard:text-parser'
