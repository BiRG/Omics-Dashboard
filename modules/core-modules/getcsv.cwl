class: CommandLineTool
cwlVersion: v1.0
id: getcsv
baseCommand:
  - getcsv.py
inputs:
  - id: collection
    type: File
    inputBinding:
      position: 0
  - id: path
    type: string
    inputBinding:
      position: 1
outputs:
  - id: csvFile
    type: File
    outputBinding:
      glob: '*.csv'
label: Get CSV
description: Get an array from the collection as a CSV file.