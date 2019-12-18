import { html, TemplateResult } from 'lit-element';
import { JudgeStatus } from './api';

const _datetime_formatter = new Intl.DateTimeFormat('ja', { weekday: 'short' });

export function format_datetime(s: string | Date): string {
  if (!(s instanceof Date)) {
    s = new Date(s);
  }
  return s.getFullYear()
    + '-' + (s.getMonth() + 1).toString().padStart(2, '0')
    + '-' + s.getDate().toString().padStart(2, '0')
    + '(' + _datetime_formatter.format(s) + ')'
    + ' ' + s.getHours().toString().padStart(2, '0')
    + ':' + s.getMinutes().toString().padStart(2, '0');
}

export function format_datetime_detail(s: string | Date): string {
  if (!(s instanceof Date)) {
    s = new Date(s);
  }
  return s.getFullYear()
    + '-' + (s.getMonth() + 1).toString().padStart(2, '0')
    + '-' + s.getDate().toString().padStart(2, '0')
    + ' ' + s.getHours().toString().padStart(2, '0')
    + ':' + s.getMinutes().toString().padStart(2, '0')
    + ':' + s.getSeconds().toString().padStart(2, '0');
}

export function format_timespan(ts: number): string {
  ts = Math.floor(ts / (60 * 1000)); // tsはミリ秒なので分未満は切り捨て
  const m = ts % 60;
  const h = Math.floor((ts / 60) % 24);
  const days = Math.floor(ts / 1440);
  let ret = '';
  if (days >= 1) {
    ret = days.toString() + ' days ';
    if (h === 0)
      return ret.trim();
  }
  ret += h.toString().padStart(2, '0') + ':' + m.toString().padStart(2, '0');
  return ret;
}

export function split_datetime(
  s: string,
): Array<string> {
  const d = new Date(s);
  return [
    d.getFullYear().toString() + '-' +
      (d.getMonth() + 1).toString().padStart(2, '0') + '-' +
      d.getDate().toString().padStart(2, '0'),
    d.getHours().toString().padStart(2, '0') + ':' +
      d.getMinutes().toString().padStart(2, '0')];
}

export function input_date_time_elements_to_iso8601(
  dateElement: HTMLInputElement,
  timeElement: HTMLInputElement,
): string | null {
  const tz = (() => {
    const offset = -new Date().getTimezoneOffset();
    if (offset === 0)
      return 'Z';
    const s = offset < 0 ? '-' : '+';
    const h = Math.floor(Math.abs(offset) / 60).toString().padStart(2, '0');
    const m = Math.floor(Math.abs(offset) % 60).toString().padStart(2, '0');
    return s + h + ':' + m;
  })();
  const pad_sec = (x: string) => {
    if (x.length == 5)
      return x + ':00';
    return x;
  };
  if (!dateElement.value || !timeElement.value)
    return null;
  return dateElement.value + 'T' + pad_sec(timeElement.value) + tz;
}

export function getSubmittionStatusMark(str: string): TemplateResult {
  if (str === JudgeStatus.Accepted) return html`<span class="AC"><x-icon>check_circle</x-icon></span>`;
  if (str === JudgeStatus.Running || str === JudgeStatus.Waiting) return html``;
  return html`<span class="WA"><x-icon>error</x-icon></span>`;
}
