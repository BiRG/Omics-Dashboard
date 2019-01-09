class: CommandLineTool
cwlVersion: v1.0
id: postcollections
baseCommand:
  - postcollections.py
inputs:
  - id: inputFiles
    type: File[]
    inputBinding:
      position: 0
  - id: omicsUrl
    type: string
    inputBinding:
      position: 1
  - id: omicsAuthToken
    type: String
    inputBinding:
      position: 2
outputs:
  - id: responses
    type: stdout
label: Post Collections(s)
doc: Upload an HDF5 file as a new collection.