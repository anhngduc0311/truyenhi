import { Injectable, Inject } from '@angular/core';
import { Title, Meta } from '@angular/platform-browser';
import { DOCUMENT } from '@angular/common';
import { ComicDetail } from '../models/comic.model';

@Injectable({
  providedIn: 'root'
})
export class SeoService {
  private defaultSiteName = 'NekoHentai';
  private defaultImage = 'https://nekohentai.lol/assets/logo.svg';
  private defaultDescription = 'NekoHentai - Web đọc truyện tranh Hentai, Manhwa 18+, Doujinshi Vietsub, Manga 18+ online cực nét chuẩn Full HD, không che, cập nhật liên tục nhanh nhất mỗi ngày. Tốc độ cao, hoàn toàn miễn phí không quảng cáo!';
  private defaultKeywords = 'nekohentai, neko hentai, doc truyen hentai, truyen hentai, hentai vietsub, hentai tieng viet, doujinshi vietsub, manhwa 18, manga 18, hentai khong che, truyen 18+, doc truyen 18, hentaivn, nhentai, hentai mau, doc truyen tranh nguoi lon, truyen hentai hay nhat';

  constructor(
    private titleService: Title,
    private metaService: Meta,
    @Inject(DOCUMENT) private document: Document
  ) {}

  /**
   * Home Page SEO (Trang Chủ)
   * High-traffic search intent for Hentai / Doujinshi / Manhwa 18+
   */
  setHomeSeo(): void {
    const title = 'NekoHentai | Đọc Truyện Hentai, Manhwa 18+, Doujinshi Vietsub Chuẩn Full HD';
    const desc = 'NekoHentai - Web đọc truyện tranh Hentai, Doujinshi, Manhwa 18+, Manga 18+ online vietsub cực nét chuẩn Full HD, không che, cập nhật nhanh nhất mỗi ngày. Đọc mượt mà, không quảng cáo!';
    this.titleService.setTitle(title);
    this.updateBasicMeta(desc, this.defaultKeywords);
    this.updateOpenGraph(title, desc, this.defaultImage, '/', 'website');
    this.updateTwitterCard(title, desc, this.defaultImage);
    this.setCanonicalUrl('/');
  }

  /**
   * Comic Detail SEO (Trang Chi Tiết Truyện)
   * Format: Đọc Truyện [Tên Truyện] [Tới Chap X] Vietsub Full HD - NekoHentai
   */
  setComicDetailSeo(comic: ComicDetail): void {
    const latestChap = comic.latestChapter?.chapterNumber ?? 'Mới Nhất';
    const fullTitle = `Đọc Truyện ${comic.title} [Tới Chap ${latestChap}] Vietsub Full HD - NekoHentai`;
    
    // Clean raw HTML or multiline text in comic description
    const rawDesc = comic.description 
      ? comic.description.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim()
      : '';
    const cleanDesc = `Đọc truyện tranh hentai ${comic.title} [Tới Chap ${latestChap}] bản dịch tiếng Việt (Vietsub) sắc nét chuẩn Full HD tại NekoHentai. ${rawDesc ? rawDesc.substring(0, 160) + '...' : 'Đọc truyện 18+ miễn phí, load nhanh không quảng cáo.'}`;
    const cover = comic.coverImage || this.defaultImage;
    const path = `/comic/${comic.slug}`;
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://nekohentai.lol';

    this.titleService.setTitle(fullTitle);

    const keywords = `${comic.title}, ${comic.title} vietsub, doc truyen ${comic.title}, ${comic.title} toi chap ${latestChap}, ${comic.title} hentai, ${comic.title} manhwa 18, truyen hentai ${comic.title}, doc hentai ${comic.title}, ${comic.author || ''}, doujinshi ${comic.title}, nekohentai`;
    this.updateBasicMeta(cleanDesc, keywords);
    this.updateOpenGraph(fullTitle, cleanDesc, cover, path, 'book');
    this.updateTwitterCard(fullTitle, cleanDesc, cover);
    this.setCanonicalUrl(path);

    // Rich Schema.org Structured Data with BreadcrumbList & Book metadata
    const schema = {
      '@context': 'https://schema.org',
      '@graph': [
        {
          '@type': 'Book',
          '@id': `${origin}${path}#book`,
          'name': comic.title,
          'alternateName': `${comic.title} [Tới Chap ${latestChap}]`,
          'author': {
            '@type': 'Person',
            'name': comic.author || 'Đang cập nhật'
          },
          'genre': comic.categories ? comic.categories.map(c => c.name) : ['Hentai', 'Doujinshi', '18+'],
          'image': cover,
          'description': cleanDesc,
          'url': `${origin}${path}`,
          'inLanguage': 'vi'
        },
        {
          '@type': 'BreadcrumbList',
          '@id': `${origin}${path}#breadcrumb`,
          'itemListElement': [
            {
              '@type': 'ListItem',
              'position': 1,
              'name': 'Trang Chủ',
              'item': `${origin}/`
            },
            {
              '@type': 'ListItem',
              'position': 2,
              'name': comic.categories?.[0]?.name || 'Hentai',
              'item': `${origin}/comics?category=${comic.categories?.[0]?.slug || ''}`
            },
            {
              '@type': 'ListItem',
              'position': 3,
              'name': `${comic.title} [Tới Chap ${latestChap}]`,
              'item': `${origin}${path}`
            }
          ]
        }
      ]
    };
    this.setJsonLd(schema);
  }

  /**
   * Chapter Read SEO (Trang Đọc Chương)
   * Format: Đọc Truyện [Tên Truyện] [Chap X / Oneshot] Vietsub Full HD - NekoHentai
   */
  setChapterReadSeo(comicTitle: string, comicSlug: string, chapterTitle: string, chapterNumber: number, coverImage?: string): void {
    const isChapOneshot = (chapterTitle && /oneshot|one-shot|1shot/i.test(chapterTitle)) || (comicTitle && /oneshot|one-shot/i.test(comicTitle)) || (comicSlug && /oneshot|one-shot/i.test(comicSlug));
    const chapText = isChapOneshot ? 'Oneshot' : `Chap ${chapterNumber}`;
    const fullTitle = isChapOneshot 
      ? `Đọc Truyện Hentai ${comicTitle} Oneshot Vietsub Full HD - NekoHentai` 
      : `Đọc Truyện Hentai ${comicTitle} Chap ${chapterNumber} Vietsub Full HD - NekoHentai`;
    const cleanDesc = isChapOneshot
      ? `Đọc truyện tranh hentai ${comicTitle} Oneshot bản dịch tiếng Việt (Vietsub) cực nét Full HD tại NekoHentai. Tốc độ tải cực nhanh, không giật lag, đọc mượt mà không quảng cáo.`
      : `Đọc truyện tranh hentai ${comicTitle} Chap ${chapterNumber} bản dịch tiếng Việt (Vietsub) cực nét Full HD tại NekoHentai. Tốc độ tải cực nhanh, không giật lag, đọc mượt mà không quảng cáo.`;
    const path = `/read/${comicSlug}/chuong-${chapterNumber}`;
    const cover = coverImage || this.defaultImage;
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://nekohentai.lol';

    this.titleService.setTitle(fullTitle);
    const keywords = isChapOneshot 
      ? `${comicTitle} oneshot, doc ${comicTitle} oneshot, doc truyen hentai ${comicTitle}, ${comicTitle} vietsub, truyen hentai ${comicTitle}, doc hentai online` 
      : `${comicTitle} chap ${chapterNumber}, doc ${comicTitle} chuong ${chapterNumber}, doc truyen hentai ${comicTitle}, ${comicTitle} vietsub, truyen hentai ${comicTitle}, doc hentai online`;
    
    this.updateBasicMeta(cleanDesc, keywords);
    this.updateOpenGraph(fullTitle, cleanDesc, cover, path, 'article');
    this.updateTwitterCard(fullTitle, cleanDesc, cover);
    this.setCanonicalUrl(path);

    const schema = {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      'itemListElement': [
        {
          '@type': 'ListItem',
          'position': 1,
          'name': 'Trang Chủ',
          'item': `${origin}/`
        },
        {
          '@type': 'ListItem',
          'position': 2,
          'name': comicTitle,
          'item': `${origin}/comic/${comicSlug}`
        },
        {
          '@type': 'ListItem',
          'position': 3,
          'name': chapText,
          'item': `${origin}${path}`
        }
      ]
    };
    this.setJsonLd(schema);
  }

  /**
   * Category / Filter / Search List SEO
   */
  setCategorySeo(categoryName?: string, query?: string): void {
    let title = 'Kho Truyện Hentai, Doujinshi, Manhwa 18+ Vietsub Hay Chọn Lọc - NekoHentai';
    let desc = 'Khám phá kho truyện tranh Hentai, Doujinshi, Manhwa 18+, Manga 18+ hay nhất chọn lọc, cập nhật chương mới nhất liên tục, hình ảnh sắc nét Full HD tại NekoHentai.';
    let keywords = 'truyen hentai online, doujinshi vietsub, manhwa 18+, manga 18+, truyen hentai hay, doc hentai khong quang cao, nekohentai';

    if (categoryName) {
      title = `Truyện Hentai Thể Loại ${categoryName} Vietsub Chọn Lọc Hay Nhất - NekoHentai`;
      desc = `Tuyển chọn danh sách truyện Hentai, Doujinshi, Manhwa 18+ thể loại ${categoryName} vietsub hay nhất, hình ảnh nét căng Full HD, cập nhật liên tục tại NekoHentai.`;
      keywords = `hentai ${categoryName}, truyen hentai ${categoryName}, doc hentai ${categoryName}, doujinshi ${categoryName}, manhwa 18 ${categoryName}, truyen 18+`;
    } else if (query) {
      title = `Tìm Kiếm Truyện Hentai: "${query}" Vietsub Chuẩn HD - NekoHentai`;
      desc = `Kết quả tìm kiếm truyện hentai, doujinshi cho từ khóa "${query}". Đọc truyện 18+ online miễn phí cập nhật mới nhất tại NekoHentai.`;
      keywords = `tim kiem hentai ${query}, truyen hentai ${query}, doc ${query} vietsub, nekohentai`;
    }

    this.titleService.setTitle(title);
    this.updateBasicMeta(desc, keywords);
    this.updateOpenGraph(title, desc, this.defaultImage, '/comics', 'website');
    this.updateTwitterCard(title, desc, this.defaultImage);
    this.setCanonicalUrl('/comics');
  }

  setGeneralSeo(title: string, description?: string, image?: string, path?: string): void {
    const fullTitle = title.includes('NekoHentai') ? title : `${title} - NekoHentai`;
    const desc = description || this.defaultDescription;
    const cover = image || this.defaultImage;
    const currentPath = path || '';

    this.titleService.setTitle(fullTitle);
    this.updateBasicMeta(desc, this.defaultKeywords);
    this.updateOpenGraph(fullTitle, desc, cover, currentPath, 'website');
    this.updateTwitterCard(fullTitle, desc, cover);
    if (path) this.setCanonicalUrl(path);
  }

  private updateBasicMeta(description: string, keywords: string): void {
    this.metaService.updateTag({ name: 'description', content: description });
    this.metaService.updateTag({ name: 'keywords', content: keywords });
    this.metaService.updateTag({ name: 'robots', content: 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1' });
  }

  private updateOpenGraph(title: string, description: string, image: string, path: string, type = 'website'): void {
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://nekohentai.lol';
    const fullUrl = `${origin}${path}`;

    this.metaService.updateTag({ property: 'og:site_name', content: this.defaultSiteName });
    this.metaService.updateTag({ property: 'og:title', content: title });
    this.metaService.updateTag({ property: 'og:description', content: description });
    this.metaService.updateTag({ property: 'og:image', content: image });
    this.metaService.updateTag({ property: 'og:url', content: fullUrl });
    this.metaService.updateTag({ property: 'og:type', content: type });
    this.metaService.updateTag({ property: 'og:locale', content: 'vi_VN' });
  }

  private updateTwitterCard(title: string, description: string, image: string): void {
    this.metaService.updateTag({ name: 'twitter:card', content: 'summary_large_image' });
    this.metaService.updateTag({ name: 'twitter:title', content: title });
    this.metaService.updateTag({ name: 'twitter:description', content: description });
    this.metaService.updateTag({ name: 'twitter:image', content: image });
  }

  private setCanonicalUrl(path: string): void {
    if (typeof window === 'undefined') return;
    const origin = window.location.origin;
    const canonicalUrl = `${origin}${path}`;

    let link: HTMLLinkElement | null = this.document.querySelector("link[rel='canonical']");
    if (!link) {
      link = this.document.createElement('link');
      link.setAttribute('rel', 'canonical');
      this.document.head.appendChild(link);
    }
    link.setAttribute('href', canonicalUrl);
  }

  private setJsonLd(schema: object): void {
    if (typeof window === 'undefined') return;
    const scriptId = 'schema-json-ld';
    let script = this.document.getElementById(scriptId) as HTMLScriptElement | null;

    if (!script) {
      script = this.document.createElement('script');
      script.id = scriptId;
      script.type = 'application/ld+json';
      this.document.head.appendChild(script);
    }
    script.text = JSON.stringify(schema);
  }
}
