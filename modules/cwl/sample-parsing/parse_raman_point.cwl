class: CommandLineTool
cwlVersion: v1.0
id: parseramanpoint
baseCommand:
  - batch_parse_raman_point.py
inputs:
  - id: input_files
    doc: Text files containing data.
    type: File[]
    inputBinding:
      position: 0
  - id: prefix
    doc: A prefix applied to the "name" field of all files.
    type: string
    inputBinding:
      position: 1
outputs:
  - id: output_files
    doc: HDF5 files containing the parsed files.
    type: File[]
    outputBinding:
      glob: '*.h5'
label: Raman Point Spectrum 
doc: Parse a text file in the .txt format, which consists of paired numeric data.
