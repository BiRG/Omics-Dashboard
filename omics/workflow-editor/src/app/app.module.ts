import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppComponent } from './app.component';
import {HttpClientModule} from '@angular/common/http';
import '@ng-bootstrap/ng-bootstrap';
import {NgbAccordionModule} from './accordion/accordion.module';
import {Router, RouterModule, Routes} from '@angular/router';
import { EditorComponent } from './editor/editor.component';

const appRoutes: Routes = [
  {
    path: ':workflowId',
    component: EditorComponent,
    pathMatch: 'full'
  }
];
@NgModule({
  declarations: [
    AppComponent,
    EditorComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    NgbAccordionModule,
    RouterModule.forRoot(appRoutes)
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
