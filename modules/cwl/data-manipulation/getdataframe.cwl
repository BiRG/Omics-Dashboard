class: CommandLineTool
cwlVersion: v1.0
id: getdataframe
baseCommand:
  - getdataframe.py
inputs:
  - id: collection
    doc: A collection id.
    type: File
    inputBinding:
      position: 0
outputs:
  - id: csvFile
    doc: A CSV file containing a Pandas DataFrame.
    type: File
    outputBinding:
      glob: '*.csv'
label: Get DataFrame
doc: Get an Pandas DataFrame as a CSV file.