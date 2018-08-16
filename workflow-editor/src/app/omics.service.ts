import { Injectable } from '@angular/core';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { Workflow } from 'cwl-svg';
import {environment} from '../environments/environment';
const baseUrl = environment.omicsUrl;

const httpOptions = {
  headers: new HttpHeaders({ 'Content-Type': 'application/json' })
};

@Injectable()
export class OmicsService {

  constructor(private http: HttpClient) { }
  getModules() {
    return this.http.get(`${baseUrl}/api/workflow_modules`, httpOptions);
  }
  getWorkflows() {
    return this.http.get(`${baseUrl}/api/workflows`, httpOptions);
  }
  getModule(path: string) {
    return this.http.get(`${baseUrl}/api/workflow_modules`, {headers: httpOptions.headers, params: {'path': path}});
  }
  getWorkflow(id: number) {
    return this.http.get(`${baseUrl}/api/workflows/${id}`);
  }
  createWorkflow(workflow: Workflow) {
    const req_body = {
      name: workflow.model.label,
      description: workflow.model.description,
      groupPermissions: 'full',
      allPermissions: 'readonly',
      userGroup: -1,
      workflow: workflow.model.serialize()
    };
    return this.http.post(`${baseUrl}/api/workflows/create`, req_body, httpOptions);
  }
  updateWorkflow(id: number, workflow: Workflow) {
    const req_body = {
      name: workflow.model.label,
      description: workflow.model.description,
      workflow: workflow.model.serialize()
    };
    return this.http.post(`${baseUrl}/api/workflows/${id}`, req_body, httpOptions);
  }
  submitJob(workflow: Workflow, job: Object) {
    // job should satisfy workflow inputs
    const req_body = {
      workflow: workflow.model.serialize(),
      job: job
    };
    return this.http.post(`${baseUrl}/jobs/submit`, req_body, httpOptions);
  }

}
