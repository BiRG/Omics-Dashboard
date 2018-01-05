cwlVersion: cwl:draft-3
class: CommandLineTool
id: 31PNMR
label: 31P-NMR
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
      value: 242778200.0
requirements:
  - class: DockerRequirement
    dockerPull: 'wsubirg/omics-dashboard:spectra-processing'
