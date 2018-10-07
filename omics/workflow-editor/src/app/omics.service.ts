import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import {WorkflowData} from './workflow-data';
import {WorkflowModuleData} from './workflow-module-data';
import {WorkflowModel} from 'cwlts/models';
import {environment} from '../environments/environment';
import {Observable} from 'rxjs';

const baseUrl = environment.omicsUrl;

const httpOptions = {
  headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
  withCredentials: true
};

@Injectable()
export class OmicsService {

  constructor(private http: HttpClient) { }
  getModules(): Observable<WorkflowModuleData[]> {
    return this.http.get<WorkflowModuleData[]>(`${baseUrl}/api/workflow_modules`, httpOptions);
  }
  getWorkflows(): Observable<any[]> {
    return this.http.get<WorkflowData[]>(`${baseUrl}/api/workflows`, httpOptions);
  }
  getModule(path: string): Observable<WorkflowModuleData> {
    return this.http.get<WorkflowModuleData>(`${baseUrl}/api/workflow_modules`,
      {headers: httpOptions.headers, withCredentials: true, params: {'path': path}});
  }
  getWorkflow(id: number): Observable<WorkflowData> {
    return this.http.get<WorkflowData>(`${baseUrl}/api/workflows/${id}`, httpOptions);
  }
  createWorkflow(workflowModel: WorkflowModel) {
    const req_body = {
      name: workflowModel.label,
      description: workflowModel.description,
      groupPermissions: 'full',
      allPermissions: 'readonly',
      userGroup: -1,
      workflow: workflowModel.serialize()
    };
    return this.http.post(`${baseUrl}/api/workflows/create`, req_body, httpOptions);
  }
  updateWorkflow(id: number, workflowModel: WorkflowModel) {
    const req_body = {
      name: workflowModel.label,
      description: workflowModel.description,
      workflow: workflowModel.serialize()
    };
    return this.http.post(`${baseUrl}/api/workflows/${id}`, req_body, httpOptions);
  }
  submitJob(workflowModel: WorkflowModel, job: Object) {
    // job should satisfy workflow inputs
    // this should be handled by the omics service?
    const req_body = {
      workflow: workflowModel.serialize(),
      job: job
    };
    return this.http.post(`${baseUrl}/jobs/submit`, req_body, httpOptions);
  }

}
