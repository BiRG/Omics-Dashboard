class: CommandLineTool
cwlVersion: v1.0
id: uploadsamples
baseCommand:
  - uploadsamples.py
inputs:
  - id: input_files
    type: File[]
    inputBinding:
      position: 0
  - id: metadata_file
    type: File
    inputBinding:
      position: 1
  - id: id_start
    type: int
    inputBinding:
      position: 2
  - id: wf_token
    type: string
    inputBinding:
      position: 3
  - id: omics_url
    type: string
    inputBinding:
      position: 4
  - id: auth_token
    type: string
    inputBinding:
      position: 5
outputs:
  - id: responses
    type: stdout
label: Upload Sample(s)
doc: Replace a sample file with an HDF5 file.
