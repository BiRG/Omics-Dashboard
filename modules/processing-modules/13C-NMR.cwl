class: CommandLineTool
cwlVersion: v1.0
id: 13CNMR
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
      valueFrom: '150819500.0'
outputs:
  - id: output
    type: File
    outputBinding:
      glob: '*.h5'
label: 13C-NMR
requirements:
  - class: DockerRequirement
    dockerPull: 'wsubirg/omics-dashboard:spectra-processing-cpu'