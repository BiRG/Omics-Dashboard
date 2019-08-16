class: CommandLineTool
cwlVersion: v1.0
id: getsplitdataframe
baseCommand:
  - get_split_dataframes.py
inputs:
  - id: input_file
    doc: A collection file.
    type: File
    inputBinding:
      position: 0
outputs:
  - id: output_file
    doc: An hdf5 file containing two dataframes, 'numeric_df' and 'label_df'.
    type: File
    outputBinding:
      glob: '*.h5'
label: Get Split DataFrames
doc: Create two dataframes from a collection, one with the numeric data in "Y" and one with only labels.