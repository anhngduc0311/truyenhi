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

export function formatChapterDisplay(
  chap?: Partial<Chapter> | null,
  comic?: Partial<Comic> | null,
  prefix: string = 'Chapter ',
  includeTitle: boolean = false
): string {
  if (isChapterOneshot(chap, comic)) {
    let t = (chap?.title || '').trim();
    t = t.replace(/^(?:chapter|chương|chap|tập)\s*[\d\.]*\s*[-:]*\s*/i, '').trim();
    return t || 'Oneshot';
  }

  const num = chap?.chapterNumber;
  if (num === undefined || num === null) {
    if (comic?.totalChapters && comic.totalChapters > 0) {
      return isComicOneshot(comic) ? 'Oneshot' : `${prefix}${comic.totalChapters}`;
    }
    return 'Đang cập nhật';
  }

  if (includeTitle && chap?.title && !chap.title.toLowerCase().startsWith('chapter') && !chap.title.toLowerCase().startsWith('chương')) {
    return `${prefix}${num} - ${chap.title}`;
  }

  return `${prefix}${num}`;
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
