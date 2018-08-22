import {WorkflowModel, WorkflowFactory} from 'cwlts/models';

export class WorkflowWrapper {
  constructor(private wfModel: WorkflowModel) { }
  addStep(wfModule: any) {
    const data = this.wfModel.serialize();
    const step = {
      run: wfModule.modulePath,
      label: wfModule.label,
      out: [],
      in: []
    };
    for (const i in wfModule.inputs) {
      if (wfModule.inputs[i].hasOwnProperty('id') && wfModule.inputs[i].hasOwnProperty('type')) {
        step.in.push({
          id: wfModule.inputs[i].id,
          type: wfModule.inputs[i].type
        });
      }
    }
    for (const i in wfModule.outputs) {
      if (wfModule.outputs[i].hasOwnProperty('id') && wfModule.outputs[i].hasOwnProperty('type')) {
        step.in.push({
          id: wfModule.outputs[i].id,
          type: wfModule.outputs[i].type
        });
      }
    }
    data.steps.push(step);
    this.wfModel = WorkflowFactory.from(data);
  }
}
