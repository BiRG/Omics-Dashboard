class: CommandLineTool
cwlVersion: v1.0
id: 1HNMR
baseCommand:
  - processNMR.py
inputs:
  - id: inputFile
    type: File
    inputBinding:
      position: 0
  - id: frequency
    type: float?
    inputBinding:
      position: 1
      valueFrom: '599733800.0'
  - id: referenceFrequency
    type: float?
    inputBinding:
      position: 2
      valueFrom: '0.0'
  - id: referenceWindow
    type: float?
    inputBinding:
      position: 3
      valueFrom: '0.03'
outputs:
  - id: output
    type: File
    outputBinding:
      glob: '*.h5'
label: 1H-NMR
requirements:
  - class: DockerRequirement
    dockerPull: 'wsubirg/omics-dashboard:spectra-processing-gpu'