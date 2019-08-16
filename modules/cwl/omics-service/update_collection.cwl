class: CommandLineTool
cwlVersion: v1.0
id: update_collection
baseCommand:
  - update_collection.py
inputs:
  - id: input_file
    type: File
    inputBinding:
      position: 0
  - id: collection_id
    type: long
    inputBinding:
      position: 1
  - id: omics_url
    type: string
    inputBinding:
      position: 2
  - id: omics_auth_token
    type: string
    inputBinding:
      position: 3
outputs:
  - id: error_responses
    type: stderr
label: Update Collections(s)
doc: Replace the file of an existing collection with input_file
