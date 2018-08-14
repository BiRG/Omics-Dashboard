class: CommandLineTool
cwlVersion: v1.0
id: uploadsamples
baseCommand:
  - uploadsamples.py
inputs:
  - id: inputFiles
    type: File[]
    inputBinding:
      position: 0
  - id: metadataFile
    type: File
    inputBinding:
      position: 1
  - id: idStart
    type: int
    inputBinding:
      position: 2
  - id: wfToken
    type: string
    inputBinding:
      position: 3
  - id: omicsUrl
    type: string
    inputBinding:
      position: 4
  - id: authToken
    type: string
    inputBinding:
      position: 5
outputs:
  - id: responses
    type: stdout
label: Upload Sample(s)
doc: Replace a sample file with an HDF5 file.