class: CommandLineTool
cwlVersion: v1.0
id: opls
baseCommand:
  - perform_opls.py
label: Perform OPLS
doc: Train and cross-validate an OPLS model.
inputs:
  - id: dataframes
    type: File
    inputBinding:
      position: 0
  - id: k
    doc: Cross-validation folds
    type: long
    inputBinding:
      position: 2
  - id: min_n_components
    doc: Minimum number of orthogonal components.
    type: long
    inputBinding:
      position: 3
  - id: inner_test_alpha
    doc: First threshold for significance
    type: float
    inputBinding:
      position: 4
  - id: outer_test_alpha
    type: float
    inputBinding:
      position: 5
  - id: metric_test_permutations
    type: long
    inputBinding:
      position: 6
  - id: inner_test_permutations
    type: long
    inputBinding:
      position: 7
  - id: outer_test_permutations
    type: long
    inputBinding:
      position: 8
  - id: force_regression
    type: boolean?
    inputBinding:
      prefix: --force_regression=
      separate: false
    default: false
outputs:
  - id: results_file
    type: File
    outputBinding:
      glob: '*.h5'
