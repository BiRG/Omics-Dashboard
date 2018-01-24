class: CommandLineTool
cwlVersion: v1.0
id: 31PNMR
baseCommand:
  - NMRfreqscale.py
inputs:
  - id: inputFile
    type: File
    inputBinding:
      position: 0
  - id: frequency
    type: float?
    inputBinding:
      position: 1
      valueFrom: '242778200.0'
outputs:
  - id: output
    type: File
    outputBinding:
      glob: '*.h5'
label: 31P-NMR
requirements:
  - class: DockerRequirement
    dockerPull: 'wsubirg/omics-dashboard:spectra-processing-gpu'