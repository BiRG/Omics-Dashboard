class: CommandLineTool
cwlVersion: v1.0
id: passthrough
baseCommand:
  - batch_process_passthrough.py
inputs:
  - id: input_files
    type: File[]
    inputBinding:
      position: 0
    doc: A list of hdf5 files each containing a spectrum in Hz. '/x' should be the abscissa and '/Y' should be the ordinate.
outputs:
  - id: output_files
    type: File[]
    outputBinding:
      glob: '*.h5'
    doc: A new set of hdf5 files each containing a spectrum in ppm. 
label: Passthrough (None)
doc: Passthrough files unprocessed.
