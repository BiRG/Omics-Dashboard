import { Component, OnInit } from '@angular/core';
import {CommandLineToolModel, WorkflowFactory} from 'cwlts/models';
import { Workflow, SVGArrangePlugin, SVGNodeMovePlugin, SVGPortDragPlugin,
  SVGEdgeHoverPlugin, SelectionPlugin, ZoomPlugin, DeletionPlugin} from 'cwl-svg';
import {OmicsService} from '../omics.service';
import { ActivatedRoute, NavigationStart } from '@angular/router';
import {WorkflowModuleData} from '../workflow-module-data';
@Component({
  selector: 'app-editor',
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss'],
  providers: [ OmicsService ]
})
export class EditorComponent implements OnInit {
  svgRoot: any;
  workflow: any;
  wfModules: {[key: string]: WorkflowModuleData[]} = {};
  uniquePackages: Set<string>;
  workflowId: number;
  title = 'Workflow Editor';
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
      const wf = WorkflowFactory.from(res.workflow as any);
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
          new ZoomPlugin()
        ]
      });
      window['wf'] = this.workflow;
    });
  }

  moduleRequested(event: any) {
    console.log(event);
    console.log(this.wfModules[event.packageName][event.moduleInd]);
  }
}
