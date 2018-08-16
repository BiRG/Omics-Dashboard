import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ModuleAccordianElementComponent } from './module-accordian-element.component';

describe('ModuleAccordianElementComponent', () => {
  let component: ModuleAccordianElementComponent;
  let fixture: ComponentFixture<ModuleAccordianElementComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ModuleAccordianElementComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ModuleAccordianElementComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
