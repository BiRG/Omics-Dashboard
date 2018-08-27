import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppComponent } from './app.component';
import { WorkflowComponent } from './workflow/workflow.component';
import { NavbarComponent } from './navbar/navbar.component';
import { ModuleSelectorComponent } from './module-selector/module-selector.component';
import { ModuleAccordianComponent } from './module-accordian/module-accordian.component';
import { ModuleAccordianElementComponent } from './module-accordian-element/module-accordian-element.component';
import {HttpClientModule, HttpClientXsrfModule} from '@angular/common/http';

@NgModule({
  declarations: [
    AppComponent,
    WorkflowComponent,
    NavbarComponent,
    ModuleSelectorComponent,
    ModuleAccordianComponent,
    ModuleAccordianElementComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
