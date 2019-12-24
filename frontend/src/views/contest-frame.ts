import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription, merge, interval } from 'rxjs';
import { BackgroundColor, MainAreaPaddingPx } from './consts';
import { router, session } from '../state';
import { format_timespan_detail } from '../utils';

@customElement('penguin-judge-contest-frame')
export class PenguinJudgeContestFrame extends LitElement {
  subscription: Subscription | null = null;
  countdownSubscription: Subscription | null = null;
  countdownVisible: boolean = false;

  connectedCallback() {
    super.connectedCallback();
    this.subscription = merge(
      session.path,
      session.contest_subject
    ).subscribe(_ => {
      const c = session.contest;
      this._unsubscribeCountdown();
      if (c) {
        const now = new Date();
        const start = new Date(c.start_time);
        const end = new Date(c.end_time);
        if (now < start) {
          this._countdownToStart(start, end);
          this.countdownSubscription = interval(100).subscribe(_ => {
            this._countdownToStart(start, end);
          });
          this.countdownVisible = true;
        } else if (start <= now && now < end) {
          this._countdownToEnd(start, end);
          this.countdownSubscription = interval(100).subscribe(_ => {
            this._countdownToEnd(start, end);
          });
          this.countdownVisible = true;
        } else {
          this.countdownVisible = false;
        }
      }
      this.requestUpdate();
    });
  }

  _updateCountdown(msg: string, delta: string) {
    const m = this.shadowRoot!.querySelector('div#countdownMsg');
    if (!m) return;
    const c = this.shadowRoot!.querySelector('div#countdown');
    if (!c) return;
    m.textContent = msg;
    c.textContent = delta;
  }

  _countdownToStart(start: Date, _: Date) {
    const delta = Math.max(0, start.getTime() - Date.now());
    const delta_str = format_timespan_detail(delta);
    this._updateCountdown('開始まであと', delta_str);
    if (delta < 0.1) {
      session.try_update_problems().then(c => {
        alert('コンテストが開始しました！問題一覧ページに移動します');
        router.navigate(router.generate('contest-tasks', {id: c.id}));
      });
    }
  }

  _countdownToEnd(_: Date, end: Date) {
    const delta = end.getTime() - Date.now();
    if (delta <= 0) {
      alert('コンテストが終了しました。お疲れ様でした。');
      this._unsubscribeCountdown();
      this.countdownVisible = false;
      this.requestUpdate();
      return;
    }
    const delta_str = format_timespan_detail(delta);
    this._updateCountdown('終了まであと', delta_str);
  }

  _unsubscribeCountdown() {
    if (this.countdownSubscription) {
      this.countdownSubscription.unsubscribe();
      this.countdownSubscription = null;
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.subscription) {
      this.subscription.unsubscribe();
      this.subscription = null;
    }
    this._unsubscribeCountdown();
  }

  render() {
    const c = session.contest;
    if (!c) return html``;
    const [tabName] = session.current_path.split('/').slice(2);

    const contest_not_started = !(session.contest && session.contest.problems);
    const tabs = [
      ['トップ', router.generate('contest-top', { id: c.id }), undefined, false],
      ['問題', router.generate('contest-tasks', { id: c.id }), 'tasks', contest_not_started],
      ['提出結果', router.generate('contest-submissions', { id: c.id }), 'submissions', contest_not_started],
      ['順位表', router.generate('contest-standings', { id: c.id }), 'standings', contest_not_started],
    ];
    const tabs_html = tabs.map(([title, link, path, disabled]) => html`
      <a is="router-link" href="${link}" class="${tabName === path ? 'selected' : ''} ${disabled ? 'disabled' : ''}">${title}</a>`);

    return html`
      <div id="frame">
        <div id="header">
          ${tabs_html}
          <a class="hidden">コードテスト</a>
          <a class="hidden">質問</a>
          <a class="hidden">解説</a>
          <div id="spacer"></div>
        </div>
        <div id="contents">
          <slot></slot>
        </div>
      </div>
      <div id="contest-clock" class="${this.countdownVisible ? '' : 'hidden'}">
        <div id="countdownMsg"></div><div id="countdown"></div>
      </div>
    `;
  }

  static get styles() {
    // #header > * の line-height は (40 - border-top-width - border-bottom-width)
    return css`
      :host {
        display: flex;
        flex-direction: column;
      }
      #frame {
        display: flex;
        flex-direction: column;
        flex-grow: 1;
      }
      #header {
        display: flex;
        position: fixed;
        left: 0;
        right: 0;
        height: 40px;
        background-color: #eee;
      }
      #header > * {
        padding-left: 2ex;
        padding-right: 2ex;
        line-height: 38px;
        border-top: 1px solid #ddd;
        border-right: 1px solid #ddd;
        border-bottom: 1px solid #ddd;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        background-color: ${BackgroundColor};
        white-space: nowrap;
      }
      #header > *.selected {
        border-bottom: unset;
      }
      #header > #spacer {
        flex-grow: 1;
        border-top: unset;
        border-right: unset;
        background-color: #eee;
      }
      #header a, #header a:link, #header a:hover, #header a:visited {
        color: #000;
        text-decoration: none;
      }
      #contents {
        margin: ${MainAreaPaddingPx}px;
        margin-top: ${40 + MainAreaPaddingPx}px;
        flex-grow: 1;
        display: flex;
      }
      #contents > ::slotted(*) {
        flex-grow: 1;
      }
      #header > a.disabled, #header > a.disabled:hover {
        color: #aaa;
        text-decoration: none;
        cursor: not-allowed;
      }
      #header > a.hidden {
        display: none;
      }
      #contest-clock {
        position: fixed;
        right: 1ex;
        bottom: 1ex;
        border: 2px solid #888;
        border-radius: 10px;
        padding: 1ex 1em;
        text-align: center;
        background-color: #fdfdfd;
      }
      #contest-clock.hidden {
        display: none;
      }
    `;
  }
}
