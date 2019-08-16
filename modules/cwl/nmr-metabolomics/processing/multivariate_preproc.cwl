class: CommandLineTool
cwlVersion: v1.0
id: multivariate_preproc
label: Multivariate Preprocessing
doc:  Pre-processing for multivariate methods like PCA and PLS.
baseCommand:
  - multivariate_preproc.py
inputs:
  - id: dataframe_file
    doc: The hdf5 file containing 'numeric_df' and 'label_df' split dataframes.
    type: File
    inputBinding:
      position: 0
  - id: scale_by_query
    doc: The mean of the records satisfying conditions on these fields will be subtracted from each record, then each
         record will be scaled by the standard deviation of the records satisfying the conditions.
    type: string?
    inputBinding:
      prefix: --scale_by=
      separate: false
  - id: model_by_query
    doc: The data points to include in the model.
    type: string?
    inputBinding:
      prefix: --model_by=
      separate: false
  - id: ignore_by_query
    doc: Data points to exclude from the model.
    type: string?
    inputBinding:
      prefix: --ignore_by=
      separate: false
  - id: pair_on_label
    doc: The paired analysis works on the difference between records in one class and other records, where the records
         are "paired" by some identity condition. The "pair on" label is used to pair all the records with equal values
         for that field.
    type: string?
    inputBinding:
      prefix: --pair_on=
      separate: false
  - id: pair_with_query
    doc: The condition which must apply for the records which will be subtracted.
    type: string?
    inputBinding:
      prefix: --pair_with=
      separate: false
outputs:
  - id: output_file
    doc: An output file containing transformed versions of the inputs.
    type: File
    outputBinding:
      glob: '*.h5'
