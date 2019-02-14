import {WorkflowModel} from 'cwlts/models';

export interface WorkflowData {
  id: number;
  name: string;
  description: string;
  creator_id: number;
  owner_id: number;
  last_editor_id: number;
  group_can_read: boolean;
  group_can_write: boolean;
  all_can_read: boolean;
  all_can_write: boolean;
  user_group_id: number;
  filename: string;
  file_type: string;
  workflow_language: string;
  analysis_ids: [number];
  workflow_definition: WorkflowModel;
}
