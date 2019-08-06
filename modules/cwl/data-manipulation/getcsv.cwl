class: CommandLineTool
cwlVersion: v1.0
id: getcsv
baseCommand:
  - getcsv.py
inputs:
  - id: inputFile
    doc: A collection file.
    type: File
    inputBinding:
      position: 0
  - id: path
    doc: A path inside the collection.
    type: string
    inputBinding:
      position: 1
outputs:
  - id: csvFile
    doc: A CSV file containing the array at path.
    type: File
    outputBinding:
      glob: '*.csv'
label: Get CSV
doc: Get an array from the collection as a CSV file.