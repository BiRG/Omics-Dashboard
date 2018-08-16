import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppComponent } from './app.component';
import { WorkflowComponent } from './workflow/workflow.component';
import { NavbarComponent } from './navbar/navbar.component';
import { ModuleSelectorComponent } from './module-selector/module-selector.component';
import { ModuleAccordianComponent } from './module-accordian/module-accordian.component';
import { ModuleAccordianElementComponent } from './module-accordian-element/module-accordian-element.component';

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
    BrowserModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
