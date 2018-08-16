import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ModuleSelectorComponent } from './module-selector.component';

describe('ModuleSelectorComponent', () => {
  let component: ModuleSelectorComponent;
  let fixture: ComponentFixture<ModuleSelectorComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ModuleSelectorComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ModuleSelectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
