import { Injectable } from '@angular/core';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { Workflow } from 'cwl-svg';
import { Observable } from 'rxjs';
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

  }
  updateWorkflow(id: number, workflow: Workflow) {

  }
  submitJob(workflow: Workflow, job: Object) {

  }

}
