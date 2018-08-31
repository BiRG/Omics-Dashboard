import { Component, OnInit } from '@angular/core';
import {WorkflowFactory} from 'cwlts/models';
import { Workflow, SVGArrangePlugin, SVGNodeMovePlugin, SVGPortDragPlugin, SVGEdgeHoverPlugin, SelectionPlugin, ZoomPlugin } from 'cwl-svg';
import {OmicsService} from './omics.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  providers: [ OmicsService ]
})
export class AppComponent implements OnInit {
  svgRoot: any;
  workflow: any;
  title = 'Workflow Editor';
  constructor(private omicsService: OmicsService) {}
  ngOnInit() {
    document.title = this.title;
    this.omicsService.getWorkflow(2).subscribe(res => {
      const wf = WorkflowFactory.from(res.workflow);
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
          new ZoomPlugin()
        ]
      });
      window['wf'] = this.workflow;
    });
  }
}
