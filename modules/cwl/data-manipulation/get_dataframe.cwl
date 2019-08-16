class: CommandLineTool
cwlVersion: v1.0
id: get_dataframe
baseCommand:
  - get_dataframe.py
inputs:
  - id: input_file
    doc: A collection.
    type: File
    inputBinding:
      position: 0
  - id: numeric_columns
    doc: Whether the column names should be just the x value or Y_x
    type: boolean
    default: true
    inputBinding:
      position: 1
  - id: include_labels
    doc: Whether to include label columns
    type: boolean
    default: true
    inputBinding:
      position: 2
  - id: include_only_labels
    doc: Whether to only include label columns. Overrides includeLabels.
    type: boolean
    default: false
    inputBinding:
      position: 3
outputs:
  - id: csv_file
    doc: A CSV file containing a Pandas DataFrame.
    type: File
    outputBinding:
      glob: '*.csv'
label: Get DataFrame
doc: Get an Pandas DataFrame as a CSV file.