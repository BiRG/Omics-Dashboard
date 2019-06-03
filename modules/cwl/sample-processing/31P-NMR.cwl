class: CommandLineTool
cwlVersion: v1.0
id: 31PNMR
baseCommand:
  - batchprocessNMR.py
inputs:
  - id: input_files
    type: File[]
    inputBinding:
      position: 0
    doc: A list of hdf5 files each containing a spectrum in Hz. '/x' should be the abscissa and '/Y' should be the ordinate.
  - id: frequency
    type: float?
    default: 242778200.0
    inputBinding:
      position: 1
    doc: The frequency of your instrument in Hz.
outputs:
  - id: output_files
    type: File[]
    outputBinding:
      glob: '*.h5'
    doc: A new set of hdf5 files each containing a spectrum in ppm.
label: 31P-NMR
doc: Process 31-P NMR spectra from frequency in Hz to chemical shift in ppm.