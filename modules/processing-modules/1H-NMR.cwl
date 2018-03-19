class: CommandLineTool
cwlVersion: v1.0
id: 1HNMR
baseCommand:
  - batchprocessNMR.py
inputs:
  - id: inputFiles
    type: File[]
    inputBinding:
      position: 0
  - id: frequency
    type: float?
    inputBinding:
      position: 1
      valueFrom: '599733800.0'
outputs:
  - id: output
    type: File[]
    outputBinding:
      glob: '*.h5'
label: 1H-NMR
