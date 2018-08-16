import { TestBed, inject } from '@angular/core/testing';

import { OmicsService } from './omics.service';

describe('OmicsService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [OmicsService]
    });
  });

  it('should be created', inject([OmicsService], (service: OmicsService) => {
    expect(service).toBeTruthy();
  }));
});
