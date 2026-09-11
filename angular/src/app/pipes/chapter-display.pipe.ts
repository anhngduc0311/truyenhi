import { Pipe, PipeTransform } from '@angular/core';
import { Comic, Chapter } from '../models/comic.model';

export function isComicOneshot(comic?: Partial<Comic> | null): boolean {
  if (!comic) return false;
  if (comic.categories && comic.categories.some(c => /oneshot|one-shot/i.test(c.name || c.slug))) {
    return true;
  }
  if (comic.title && /oneshot|one-shot/i.test(comic.title)) {
    return true;
  }
  if (comic.slug && /oneshot|one-shot/i.test(comic.slug)) {
    return true;
  }
  if (comic.status && /oneshot/i.test(comic.status)) {
    return true;
  }
  if (comic.latestChapter?.title && /oneshot|one-shot|1shot/i.test(comic.latestChapter.title)) {
    return true;
  }
  if (comic.recentChapters && comic.recentChapters.length === 1 && comic.recentChapters[0]?.title && /oneshot|one-shot|1shot/i.test(comic.recentChapters[0].title)) {
    return true;
  }
  return false;
}

export function isChapterOneshot(chap?: Partial<Chapter> | null, comic?: Partial<Comic> | null): boolean {
  if (chap?.title && /oneshot|one-shot|1shot/i.test(chap.title)) {
    return true;
  }
  if (isComicOneshot(comic)) {
    if (!chap || chap.chapterNumber === 1 || comic?.totalChapters === 1 || (comic?.recentChapters && comic.recentChapters.length <= 1)) {
      return true;
    }
  }
  return false;
}

/**
 * Trích xuất phụ đề chapter thực tế, tự động loại bỏ các tiền tố trùng lặp:
 * Ví dụ:
 *  - "Chap 4" -> "" (không có phụ đề, chỉ là số thứ tự chap)
 *  - "Chapter 4" -> ""
 *  - "Chương 4" -> ""
 *  - "4" -> ""
 *  - "Chapter 4 - Chap 4" -> ""
 *  - "Chap 4: Cuộc chiến" -> "Cuộc chiến"
 *  - "Chapter 4 - Cuộc chiến" -> "Cuộc chiến"
 *  - "Cuộc chiến" -> "Cuộc chiến"
 */
export function extractChapterSubtitle(title?: string | null, chapterNumber?: number | string | null): string {
  if (!title) return '';
  let clean = title.trim();
  if (!clean) return '';

  // Oneshot check
  if (/oneshot|one-shot|1shot/i.test(clean)) {
    clean = clean.replace(/^(?:chapter|chương|chap|tập|ep|episode)\s*[\d\.]*\s*[-:–—.]*\s*/i, '').trim();
    return clean || '';
  }

  let prev = '';
  // Vòng lặp giải quyết chuỗi tiền tố lặp (ví dụ "Chapter 4 - Chap 4: ...")
  while (clean !== prev) {
    prev = clean;

    // 1. Xóa các từ tiền tố chương: Chap / Chapter / Chương / Tập / Ep / Episode / Vol / Volume kèm số (hoặc không số)
    clean = clean.replace(/^(?:(?:vol|volume)\s*[\d\.]*\s*[-:–—.]*\s*)?(?:chapter|chương|chap|tập|ep|episode)\s*[\d\.]*\s*[-:–—.]*\s*/i, '').trim();

    // 2. Xóa số thứ tự kèm dấu phân cách (nếu trùng chapterNumber, ví dụ: chapterNumber = 4 và bắt đầu bằng "4 - " hay "04: ")
    if (chapterNumber !== undefined && chapterNumber !== null) {
      const numStr = `${chapterNumber}`.trim();
      const escapedNum = numStr.replace('.', '\\.');
      clean = clean.replace(new RegExp(`^0*${escapedNum}\\s*[-:–—.]+\\s*`, 'i'), '').trim();

      // Nếu phần còn lại chính là số thứ tự
      if (clean === numStr || clean === `0${numStr}` || (/^0*\d+(\.\d+)?$/.test(clean) && parseFloat(clean) === parseFloat(numStr))) {
        clean = '';
        break;
      }
    }
  }

  // Xóa dấu câu thừa ở đầu và cuối nếu có
  clean = clean.replace(/^[-:–—.\s]+/, '').replace(/[-:–—.\s]+$/, '').trim();

  return clean;
}

export function formatChapterDisplay(
  chap?: Partial<Chapter> | null,
  comic?: Partial<Comic> | null,
  prefix: string = 'Chapter ',
  includeTitle: boolean = false
): string {
  if (isChapterOneshot(chap, comic)) {
    const subtitle = extractChapterSubtitle(chap?.title, chap?.chapterNumber);
    return subtitle ? `Oneshot - ${subtitle}` : 'Oneshot';
  }

  const num = chap?.chapterNumber;
  if (num === undefined || num === null) {
    if (comic?.totalChapters && comic.totalChapters > 0) {
      return isComicOneshot(comic) ? 'Oneshot' : `${prefix}${comic.totalChapters}`;
    }
    return 'Đang cập nhật';
  }

  const baseName = `${prefix}${num}`;

  if (includeTitle && chap?.title) {
    const subtitle = extractChapterSubtitle(chap.title, num);
    if (subtitle) {
      return `${baseName} - ${subtitle}`;
    }
  }

  return baseName;
}

@Pipe({
  name: 'chapterDisplay',
  standalone: true
})
export class ChapterDisplayPipe implements PipeTransform {
  transform(
    chap?: Partial<Chapter> | null,
    comic?: Partial<Comic> | null,
    prefix: string = 'Chapter ',
    includeTitle: boolean = false
  ): string {
    return formatChapterDisplay(chap, comic, prefix, includeTitle);
  }
}
