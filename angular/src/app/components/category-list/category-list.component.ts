import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ComicService } from '../../services/comic.service';
import { SeoService } from '../../services/seo.service';
import { Category } from '../../models/comic.model';

@Component({
  selector: 'app-category-list',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './category-list.component.html',
  styleUrls: ['./category-list.component.scss']
})
export class CategoryListComponent implements OnInit {
  categories: Category[] = [];
  isLoading: boolean = true;
  skeletonCategories: number[] = Array(8).fill(0);

  constructor(
    private comicService: ComicService,
    private seoService: SeoService
  ) {}

  ngOnInit(): void {
    this.seoService.setGeneralSeo(
      'Kho Thể Loại Truyện Hentai, Doujinshi, Manhwa 18+ Vietsub Hay Nhất',
      'Khám phá danh sách hơn 100+ thể loại truyện Hentai, Doujinshi, Manhwa 18+, Manga 18+ phong phú được cập nhật liên tục tại NekoHentai.',
      undefined,
      '/categories'
    );
    this.isLoading = true;
    this.comicService.getCategories().subscribe({
      next: (cats) => {
        this.categories = cats;
        this.isLoading = false;
      },
      error: () => (this.isLoading = false)
    });
  }
}
