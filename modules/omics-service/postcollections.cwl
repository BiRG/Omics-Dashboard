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
  - id: authToken
    type: String
    inputBinding
      position: 1
outputs:
  - id: responses
    type: stdout

label: Post Collections(s)