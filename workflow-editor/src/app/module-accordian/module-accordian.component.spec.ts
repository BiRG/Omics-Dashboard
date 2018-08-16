import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ModuleAccordianComponent } from './module-accordian.component';

describe('ModuleAccordianComponent', () => {
  let component: ModuleAccordianComponent;
  let fixture: ComponentFixture<ModuleAccordianComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ModuleAccordianComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ModuleAccordianComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
