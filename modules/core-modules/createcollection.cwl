class: CommandLineTool
cwlVersion: v1.0
id: createcollection
baseCommand:
  - createcollection.py
inputs:
  - id: inputFile
    type: File
    inputBinding:
      position: 0
  - id: metadataFile
    type: File
    inputBinding:
      position: 1
  - id: dataDirectory
    type: Directory
    inputBinding:
      position: 2
outputs:
  - id: output
    type: File
    outputBinding:
      glob: '*.h5'
label: Create Collection
requirements:
  - class: DockerRequirement
    dockerPull: 'wsubirg/omics-dashboard:core'