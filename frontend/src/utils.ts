const _datetime_formatter = new Intl.DateTimeFormat('ja', {weekday: 'short'});


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

export function check_contest_status(start: string | Date, end: string | Date) {
  if (!(start instanceof Date)) {
      start = new Date(start);
  }
  if (!(end instanceof Date)) {
      end = new Date(end);
  }
  var now = new Date();

  if (now.getTime() < start.getTime()) {
    return 'scheduled';
  } else if (now.getTime() < end.getTime()) {
    return 'running';
  } else {
    return 'finished';
  }
}