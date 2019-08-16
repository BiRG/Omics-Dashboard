class: CommandLineTool
cwlVersion: v1.0
id: getcollection
baseCommand:
  - get_collection.py
inputs:
  - id: collection_id
    type: int
    inputBinding:
      position: 0
  - id: omics_url
    type: string
    inputBinding:
      position: 1
  - id: omics_auth_token
    type: string
    inputBinding:
      position: 2
outputs:
  - id: collection_file
    type: File
    outputBinding:
      glob: '*.h5'
label: Get Collection
doc: Get a collection as an HDF5 file.
