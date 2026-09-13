import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { UserService } from '../../services/user.service';
import { ReadingHistory } from '../../models/user.model';
import { ChapterDisplayPipe } from '../../pipes/chapter-display.pipe';
import { TimeAgoPipe } from '../../pipes/time-ago.pipe';

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [CommonModule, RouterModule, ChapterDisplayPipe, TimeAgoPipe],
  templateUrl: './history.component.html',
  styleUrls: ['./history.component.scss']
})
export class HistoryComponent implements OnInit {
  historyItems: ReadingHistory[] = [];
  isLoading: boolean = true;

  constructor(private userService: UserService) {}

  ngOnInit(): void {
    this.userService.getHistory().subscribe({
      next: (data) => {
        this.historyItems = data;
        this.isLoading = false;
      },
      error: () => (this.isLoading = false)
    });
  }

  trackByHistoryId(index: number, item: ReadingHistory): number {
    return item?.id ?? index;
  }
}
