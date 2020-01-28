class: CommandLineTool
cwlVersion: v1.0
id: batchfigureexport
baseCommand:
  - batch_figure_export.py
inputs:
  - id: param_file
    type: File
    inputBinding:
      position: 0
    doc: A JSON file containing the parameters for the image export (width, height, width/height units, DPI, and file formats).
  - id: figure_file
    type: File[]
    inputBinding:
      position: 1
    doc: A JSON file containing a list of Plotly figures.
outputs:
  - id: figure_archive
    type: File
    outputBinding:
      glob: '*.zip'
label: Get Collection
doc: Export a list of Plotly figures as images in a ZIP archive.
