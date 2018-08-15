import { Component } from '@angular/core';
import {WorkflowFactory} from 'cwlts/models';
import {Workflow} from 'cwl-svg';
import {SVGArrangePlugin} from 'cwl-svg';
import {SVGNodeMovePlugin} from 'cwl-svg';
import {SVGPortDragPlugin} from 'cwl-svg';
import {SelectionPlugin} from 'cwl-svg';
import {SVGEdgeHoverPlugin} from 'cwl-svg';
import {ZoomPlugin} from 'cwl-svg';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'app';
}
