import { Component, ElementRef, OnInit, OnDestroy, AfterViewInit, ViewChild, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ComicService } from '../../services/comic.service';
import { SeoService } from '../../services/seo.service';
import { Comic, Category } from '../../models/comic.model';
import { ChapterDisplayPipe } from '../../pipes/chapter-display.pipe';
import { TimeAgoPipe } from '../../pipes/time-ago.pipe';
import { CompactNumberPipe } from '../../pipes/compact-number.pipe';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterModule, ChapterDisplayPipe, TimeAgoPipe, CompactNumberPipe],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('suggestContainer') suggestContainer?: ElementRef<HTMLDivElement>;

  latestComics: Comic[] = [];
  hotComics: Comic[] = [];
  categories: Category[] = [];

  selectedFilter: string = 'all';
  filterChips = [
    { label: 'Tất Cả', key: 'all', icon: 'fa-globe' },
    { label: 'Hot Tuần', key: 'hot', icon: 'fa-fire' },
    { label: 'Manhwa', key: 'manhwa', icon: 'fa-flag' }
  ];

  isLoading: boolean = true;
  isLoadingHot: boolean = true;
  page: number = 1;

  skeletonHotCards: number[] = Array(8).fill(0);
  skeletonCards: number[] = Array(12).fill(0);

  private suggestTimer?: any;
  private isSuggestHovered: boolean = false;
  displayHotComics: Comic[] = [];
  private isSliding: boolean = false;

  constructor(
    private comicService: ComicService,
    private seoService: SeoService,
    private ngZone: NgZone
  ) { }

  ngOnInit(): void {
    this.seoService.setHomeSeo();
    this.loadData();
    this.startSuggestAutoScroll();
  }

  ngAfterViewInit(): void {
    if (this.suggestContainer?.nativeElement) {
      // Attach passive scroll listener outside Angular zone to achieve 60-120fps smooth scrolling
      this.ngZone.runOutsideAngular(() => {
        this.suggestContainer!.nativeElement.addEventListener(
          'scroll',
          () => this.checkInfiniteLoopReset(),
          { passive: true }
        );
      });
    }
  }

  ngOnDestroy(): void {
    this.stopSuggestAutoScroll();
  }

  loadData(): void {
    this.isLoading = true;
    this.isLoadingHot = true;

    // Load Hot Comics for Suggested Carousel (15 items)
    this.comicService.getFeaturedComics('hot', 15).subscribe({
      next: (data) => {
        this.hotComics = data;
        // Duplicate items for seamless continuous infinite loop (TruyenGG style)
        this.displayHotComics = data.length > 0 ? [...data, ...data, ...data] : [];
        this.isLoadingHot = false;
        setTimeout(() => this.startSuggestAutoScroll(), 300);
      },
      error: () => {
        this.isLoadingHot = false;
      }
    });

    // Load Latest Comics for Grid
    this.comicService.getLatestComics(24).subscribe({
      next: (data) => {
        this.latestComics = data;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  get itemWidth(): number {
    if (!this.suggestContainer?.nativeElement) return 174;
    const firstCard = this.suggestContainer.nativeElement.querySelector('.suggest-card') as HTMLElement;
    return firstCard ? (firstCard.offsetWidth + 14) : 174;
  }

  startSuggestAutoScroll(): void {
    this.stopSuggestAutoScroll();
    // Run timer outside Angular Zone to avoid triggering global Change Detection every 3.5s
    this.ngZone.runOutsideAngular(() => {
      this.suggestTimer = setInterval(() => {
        if (this.isSuggestHovered || !this.suggestContainer?.nativeElement || this.isSliding) return;
        this.scrollSuggest('right');
      }, 3500);
    });
  }

  stopSuggestAutoScroll(): void {
    if (this.suggestTimer) {
      clearInterval(this.suggestTimer);
      this.suggestTimer = undefined;
    }
  }

  onSuggestMouseEnter(): void {
    this.isSuggestHovered = true;
  }

  onSuggestMouseLeave(): void {
    this.isSuggestHovered = false;
  }

  private checkInfiniteLoopReset(): void {
    if (!this.suggestContainer?.nativeElement) return;
    const el = this.suggestContainer.nativeElement;
    const oneSetWidth = el.scrollWidth / 3;
    if (oneSetWidth <= 0) return;

    if (el.scrollLeft >= oneSetWidth * 2) {
      el.scrollLeft -= oneSetWidth;
    }
  }

  setFilter(key: string): void {
    this.selectedFilter = key;
  }

  get filteredComics(): Comic[] {
    if (this.selectedFilter === 'all') return this.latestComics;
    if (this.selectedFilter === 'hot') return this.hotComics;
    if (this.selectedFilter === 'new') return this.latestComics.slice(0, 12);
    return this.latestComics.filter(c =>
      c.categories?.some(cat => cat.slug.toLowerCase().includes(this.selectedFilter) || cat.name.toLowerCase().includes(this.selectedFilter))
    );
  }

  scrollSuggest(direction: 'left' | 'right'): void {
    if (!this.suggestContainer?.nativeElement || this.isSliding) return;
    const el = this.suggestContainer.nativeElement;
    const step = this.itemWidth * (el.clientWidth > 768 ? 2 : 1);
    const oneSetWidth = el.scrollWidth / 3;

    this.isSliding = true;

    if (direction === 'left') {
      if (el.scrollLeft <= 10 && oneSetWidth > 0) {
        el.scrollLeft = oneSetWidth;
      }
      el.scrollBy({ left: -step, behavior: 'smooth' });
    } else {
      if (el.scrollLeft >= oneSetWidth * 2 && oneSetWidth > 0) {
        el.scrollLeft -= oneSetWidth;
      }
      el.scrollBy({ left: step, behavior: 'smooth' });
    }

    setTimeout(() => {
      this.isSliding = false;
      this.checkInfiniteLoopReset();
    }, 450);

    this.startSuggestAutoScroll();
  }

  scrollToTop(): void {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  onImgError(event: Event): void {
    const target = event.target as HTMLImageElement;
    if (target) {
      target.src = 'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=300&q=80';
    }
  }

  // DOM Optimization: TrackBy functions
  trackByIndex(index: number): number {
    return index;
  }

  trackByComicId(index: number, comic: Comic): number {
    return comic.id;
  }

  trackByChapterId(index: number, ch: any): number {
    return ch?.id || index;
  }
}
