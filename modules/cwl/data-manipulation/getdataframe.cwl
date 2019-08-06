class: CommandLineTool
cwlVersion: v1.0
id: getdataframe
baseCommand:
  - getdataframe.py
inputs:
  - id: inputFile
    doc: A collection.
    type: File
    inputBinding:
      position: 0
  - id: numericColumns
    doc: Whether the column names should be just the x value or Y_x
    type: boolean
    default: true
    inputBinding:
      position: 1
  - id: includeLabels
    doc: Whether to include label columns
    type: boolean
    default: true
    inputBinding:
      position: 2
  - id: includeOnlyLabels
    doc: Whether to only include label columns. Overrides includeLabels.
    type: boolean
    default: false
    inputBinding:
      position: 3
outputs:
  - id: csvFile
    doc: A CSV file containing a Pandas DataFrame.
    type: File
    outputBinding:
      glob: '*.csv'
label: Get DataFrame
doc: Get an Pandas DataFrame as a CSV file.