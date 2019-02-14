import {CommandLineToolModel} from 'cwlts/models';

export interface WorkflowModuleData {
  id: number;
  path: string;
  label: string;
  description: string;
  package: string;
  package_description: string;
  subpackage: string;
  subpackage_description: string;
  tool_definition: CommandLineToolModel;
}

