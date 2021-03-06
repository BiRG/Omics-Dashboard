import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppComponent } from './app.component';
import { HttpClientModule } from '@angular/common/http';
import { NgbAccordionModule } from './accordion/accordion.module';
import { RouterModule, Routes } from '@angular/router';
import { EditorComponent } from './editor/editor.component';
import {OmicsService} from './omics.service';

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
    RouterModule.forRoot(appRoutes, {useHash: true})
  ],
  providers: [OmicsService],
  bootstrap: [AppComponent]
})
export class AppModule { }
