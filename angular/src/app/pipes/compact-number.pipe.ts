import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'compactNumber',
  standalone: true,
  pure: true
})
export class CompactNumberPipe implements PipeTransform {
  transform(num?: number | string | null): string {
    if (num === null || num === undefined) return '0';
    const n = typeof num === 'string' ? parseFloat(num) : num;
    if (isNaN(n) || n === 0) return '0';
    if (n >= 1000000) return (n / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    return Math.floor(n).toString();
  }
}
