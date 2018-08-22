import {Component, Inject, OnInit} from '@angular/core';
import {WorkflowFactory} from 'cwlts/models';
import {Workflow} from 'cwl-svg';
import { SVGArrangePlugin, SVGNodeMovePlugin, SVGPortDragPlugin, SelectionPlugin,
  SVGEdgeHoverPlugin, ZoomPlugin } from 'cwl-svg';
import {OmicsService} from '../omics.service';
import {WorkflowWrapper} from '../workflow-wrapper';

@Component({
  selector: 'app-workflow',
  templateUrl: './workflow.component.html',
  styleUrls: ['./workflow.component.css']
})
export class WorkflowComponent implements OnInit {
  constructor(private workflow: Workflow) {}

  ngOnInit() {
    window['wf'] = this.workflow;
  }
  addStep(wfModule: any) {
    const wrapper = new WorkflowWrapper(this.workflow.model);
    wrapper.addStep(wfModule);
  }
}
