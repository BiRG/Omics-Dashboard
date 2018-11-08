import {WorkflowModel} from 'cwlts/models';

export interface WorkflowData {
  id: number;
  name: string;
  description: string;
  owner: number;
  createdBy: number;
  userGroup: number;
  groupPermissions: string;
  allPermissions: string;
  workflow: WorkflowModel;
}
