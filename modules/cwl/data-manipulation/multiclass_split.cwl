class: CommandLineTool
cwlVersion: v1.0
id: multiclasssplit
baseCommand:
  - multiclass_split.py
inputs:
  - id: input_file
    doc: A collection file.
    type: File
    inputBinding:
      position: 0
  - id: target
    doc: Column name of target variable.
    type: string
    inputBinding:
      position: 1
  - id: one_v_one
    doc: Whether to do one vs. one split
    type: boolean
    inputBinding:
      prefix: --one_v_one
      separate: false
    default: false
  - id: one_v_all
    doc: Whether to do one vs. rest split
    type: boolean
    inputBinding:
      prefix: --one_v_all
      separate: false
    default: false
outputs:
  - id: output_file
    doc: An hdf5 file containing several groups, each with two dataframes, 'numeric_df' and 'label_df'.
    type: File
    outputBinding:
      glob: '*.h5'
label: Multiclass split
doc: Create two dataframes from a collection, one with the numeric data in "Y" and one with only labels.
