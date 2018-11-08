import {CommandLineToolModel} from 'cwlts/models';

export interface WorkflowModuleData {
  packageName: string;
  label: string;
  description: string;
  package: string;
  path: string;
  subPackage: string;
  subpackageDescription: string;
  toolDefinition: CommandLineToolModel;
}
