class: CommandLineTool
cwlVersion: v1.0
id: getdataframe
baseCommand:
  - getdataframe.py
inputs:
  - id: collection
    type: File
    inputBinding:
      position: 0
outputs:
  - id: csvFile
    type: File
    outputBinding:
      glob: '*.csv'
label: Get DataFrame
description: Get an Pandas DataFrame as a CSV file.