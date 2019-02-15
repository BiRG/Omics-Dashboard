import {AfterViewInit, Component, HostListener, OnInit} from '@angular/core';
import {CommandLineToolModel, WorkflowFactory} from 'cwlts/models';
import { Workflow, SVGArrangePlugin, SVGNodeMovePlugin, SVGPortDragPlugin,
  SVGEdgeHoverPlugin, SelectionPlugin, ZoomPlugin, DeletionPlugin} from 'cwl-svg';
import {OmicsService} from '../omics.service';
import { ActivatedRoute, NavigationStart } from '@angular/router';
import {WorkflowModuleData} from '../workflow-module-data';
import {Subject} from 'rxjs';
import {environment} from '../../environments/environment';
@Component({
  selector: 'app-editor',
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss'],
  providers: [ OmicsService ]
})
export class EditorComponent implements OnInit {
  svgRoot: any;
  workflow: Workflow;
  wfModules: {[key: string]: WorkflowModuleData[]} = {};
  uniquePackages: Set<string>;
  workflowId: number;
  title = 'Workflow Editor';
  omicsUrl = environment.omicsUrl;
  constructor(private omicsService: OmicsService, private route: ActivatedRoute) {
    this.omicsService.getModules().subscribe(res => {
      this.uniquePackages = new Set(res.map(item => item.package));
      this.uniquePackages.forEach(packageName => {
        this.wfModules[packageName] = res.filter(item => item.package === packageName);
      });
    });
  }

  ngOnInit() {
    document.title = this.title;
    this.workflowId = Number(this.route.snapshot.paramMap.get('workflowId'));
    this.omicsService.getWorkflow(this.workflowId).subscribe(res => {
      const wf = WorkflowFactory.from(res.workflow_definition as any);
      this.svgRoot = document.getElementById('svg');
      this.workflow = new Workflow({
        model: wf,
        svgRoot: this.svgRoot,
        plugins: [
          new SVGArrangePlugin(),
          new SVGEdgeHoverPlugin(),
          new SVGNodeMovePlugin(),
          new SVGPortDragPlugin(),
          new SelectionPlugin(),
          new DeletionPlugin(),
          new ZoomPlugin(),
        ]
      });
      window['wf'] = this.workflow;
      this.workflow.getPlugin(ZoomPlugin).attachWheelListener();
    });
  }

  moduleRequested(event: any) {
    console.log(event);
    console.log(this.wfModules[event.packageName][event.moduleInd].tool_definition);
    const newStep: CommandLineToolModel = this.wfModules[event.packageName][event.moduleInd].tool_definition;
    // @ts-ignore
    this.workflow.model.addStepFromProcess(newStep);
    for (const step of this.workflow.model.steps) {
      step.in.forEach(input => {
        this.workflow.model.includePort(input);
        if (input.id === 'omics_auth_token') {
          const tokenInput = this.workflow.model.inputs.find(elem => elem.id === 'omics_auth_token');
          if (tokenInput === undefined) {
            this.workflow.model.createInputFromPort(input);
          } else {
            this.workflow.model.connect(tokenInput, input);
          }
        }
        if (input.id === 'omics_url') {
          const urlInput = this.workflow.model.inputs.find(elem => elem.id === 'omics_url');
          if (urlInput === undefined) {
            this.workflow.model.createInputFromPort(input);
          } else {
            this.workflow.model.connect(urlInput, input);
          }
        }
      });
    }
  }

  onResetClicked() {
    this.omicsService.getWorkflow(this.workflowId).subscribe(res => {
      this.workflow = new Workflow({
        model: WorkflowFactory.from(res.workflow_definition as any),
        svgRoot: this.svgRoot,
        plugins: [
          new SVGArrangePlugin(),
          new SVGEdgeHoverPlugin(),
          new SVGNodeMovePlugin(),
          new SVGPortDragPlugin(),
          new SelectionPlugin(),
          new DeletionPlugin(),
          new ZoomPlugin(),
        ]
      });
    });
  }

  onUpdateClicked() {
    this.omicsService.updateWorkflow(this.workflowId, this.workflow.model).subscribe();
  }
  @HostListener('wheel', ['$event'])
  onMouseWheel(event: WheelEvent) {
    console.log('onMouseWheel');
    const scale       = this.workflow.scale;
    const scaleUpdate = scale - event.deltaY / 50;

    const zoomingOut = scaleUpdate < scale;
    const zoomingIn = scaleUpdate > scale;

    if (zoomingIn && this.workflow.maxScale < scaleUpdate) {
      return;
    }

    if (zoomingOut && this.workflow.minScale > scaleUpdate) {
      return;
    }

    this.workflow.scaleAtPoint(scaleUpdate, event.clientX, event.clientY);
    event.stopPropagation();
  }


}
