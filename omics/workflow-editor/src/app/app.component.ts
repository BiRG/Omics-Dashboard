import { Component, OnInit } from '@angular/core';
import {OmicsService} from './omics.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  providers: [OmicsService]
})
export class AppComponent implements OnInit {
  constructor(private omicsService: OmicsService) {
    this.omicsService.getUser().subscribe(res => {
      if (res.theme === 'dark') {
        require('style-loader!./../styles_dark.scss');
      } else {
        require('style-loader!./../styles_light.scss');
      }
    });
  }
  ngOnInit() {
  }
}
