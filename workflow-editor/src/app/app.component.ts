import {Component, ViewChild} from '@angular/core';
import {WorkflowFactory} from 'cwlts/models';
import {Workflow} from 'cwl-svg';
import {SVGArrangePlugin} from 'cwl-svg';
import {SVGNodeMovePlugin} from 'cwl-svg';
import {SVGPortDragPlugin} from 'cwl-svg';
import {SelectionPlugin} from 'cwl-svg';
import {SVGEdgeHoverPlugin} from 'cwl-svg';
import {ZoomPlugin} from 'cwl-svg';
import {OmicsService} from './omics.service';
import {WorkflowComponent} from './workflow/workflow.component';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  @ViewChild(WorkflowComponent) wfComponent: WorkflowComponent;
  constructor(private omicsService: OmicsService) {
    const svgRoot = document.getElementById('svg') as any;
    this.omicsService.getWorkflow(1).subscribe(wfData => {
      const wf = WorkflowFactory.from(wfData);
      const workflow = new Workflow({
        model: wf,
        svgRoot: svgRoot,
        plugins: [
          new SVGArrangePlugin(),
          new SVGEdgeHoverPlugin(),
          new SVGNodeMovePlugin({movementSpeed: 10}),
          new SVGPortDragPlugin(),
          new SelectionPlugin(),
          new ZoomPlugin()
        ]
      });
      this.wfComponent = new WorkflowComponent(workflow);
    });

  }
  title = 'app';
}


