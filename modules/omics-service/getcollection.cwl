class: CommandLineTool
cwlVersion: v1.0
id: getcollection
baseCommand:
  - getcollection.py
inputs:
  - id: collectionId
    type: int
    inputBinding:
      position: 0
  - id: omicsUrl
    type: string
    inputBinding:
      position: 1
  - id: authToken
    type: string
    inputBinding:
      position: 2
outputs:
  - id: collectionFile
    type: File
    outputBinding:
      glob: '*.h5'
label: Get Collection
doc: Get a collection as an HDF5 file.
