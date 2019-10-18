import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription } from 'rxjs';
import { BackgroundColor, MainAreaPaddingPx } from './consts';
import { router, session } from './state';
import { anchor_handler as _anchor_handler } from './utils';

@customElement('penguin-judge-contest-frame')
export class PenguinJudgeContestFrame extends LitElement {
  subscription: Subscription | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.subscription = session.path.subscribe(_ => {
      this.requestUpdate();
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.subscription) {
      this.subscription.unsubscribe();
      this.subscription = null;
    }
  }

  render() {
    const c = session.contest;
    if (!c) return html``;
    const items = session.current_path.split('/').slice(2);

    const tabs = [
      ['トップ', router.generate('contest-top', {id: c.id}), false],
      ['問題', router.generate('contest-tasks', {id: c.id}), items.length > 0 && items[0] === 'tasks'],
      ['提出結果', router.generate('contest-submissions-me', {id: c.id}), items.length > 0 && items[0] === 'submissions'],
    ];
    const has_selected = tabs.reduce((accum, v) => {
      return accum || v[2];
    }, false);
    if (!has_selected)
      tabs[0][2] = true;
    const tabs_html: any = [];
    tabs.forEach((e) => {
      tabs_html.push(html`<a @click="${this.anchor_handler}" href="${e[1]}" class="${e[2] ? 'selected' : ''}">${e[0]}</a>`);
    });

    return html`
      <div id="frame">
        <div id="header">
          ${tabs_html}
          <a class="disabled">順位表</a>
          <a class="disabled">コードテスト</a>
          <a class="disabled">質問</a>
          <a class="disabled">解説</a>
          <div id="spacer"></div>
        </div>
        <div id="contents">
          <slot></slot>
        </div>
      </div>
    `;
  }

  anchor_handler(e: MouseEvent): void {
    const target = <HTMLElement>e.target;
    if (!target) return;
    _anchor_handler(e);
    target.blur();
  }

  static get styles() {
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
      }
      #header > * {
        padding: 1ex 2ex;
        border-top: 1px solid #ddd;
        border-right: 1px solid #ddd;
        border-bottom: 1px solid #ddd;
      }
      #header > *.selected {
        background-color: ${BackgroundColor};
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
        flex-grow: 1;
        display: flex;
      }
      #contents > * {
        flex-grow: 1;
      }
      #header > .disabled, #header > .disabled:hover {
        color: #aaa;
        text-decoration: none;
        cursor: not-allowed;
      }
    `;
  }
}