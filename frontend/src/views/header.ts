import { customElement, LitElement, html, css, unsafeCSS } from 'lit-element';
import { HeaderHeight, HeaderHeightPx } from './consts';
import { router, session } from '../state';

@customElement('penguin-judge-header')
export class PenguinJudgeHeaderElement extends LitElement {
  constructor() {
    super();
    session.contest_subject.subscribe(_ => {
      this.requestUpdate();
    });
    session.current_user.subscribe(_ => {
      this.requestUpdate();
    });
  }

  render() {
    let title = 'Penguin Judge';
    let title_link = router.generate('home');
    if (session.contest) {
      title = session.contest.title;
      title_link = router.generate('contest-top', { id: session.contest.id });
    }

    let user_area;
    if (session.current_user.value) {
      user_area = html`
        <x-icon>person</x-icon>
        <span>${session.current_user.value.name}</span>
        <span class="dropdown-caret"></span>`;
    } else {
      user_area = html`<a is="router-link" href="${router.generate('login')}">ログイン</a>`
    }
    return html`
      <span id="icon-area">
        <a is="router-link" href="${router.generate('home')}"><img id="icon" src="/images/penguin.png"></a>
      </span>
      <span id="title">
        <a href="${title_link}" is="router-link">${title}</a>
      </span>
      <span id="extra">
        <span tabindex="0">
          <a is="router-link" href="${router.generate('home')}" title="ホームに戻る">
            <x-icon>home</x-icon>
          </a>
        </span>
        <span tabindex="0">
          <a is="router-link" href="${router.generate('contests')}" title="コンテスト一覧">
            <x-icon>insert_chart_outlined</x-icon>
          </a>
        </span>
        <span tabindex="0">${user_area}</span>
      </span>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: flex;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: ${HeaderHeight};
        background-color: #eee;
        align-items: center;
      }
      #icon-area {
        height: ${HeaderHeight};
        width: ${HeaderHeight};
        display: flex;
        align-items: center;
        justify-content: center;
      }
      #icon {
        height: ${unsafeCSS(HeaderHeightPx * 0.7)}px;
      }
      a {
        text-decoration: none;
      }
      #title {
        font-weight: bold;
        font-size: 130%;
      }
      #title a {
        color: black;
      }
      #extra {
        flex-grow: 1;
        text-align: right;
        margin-right: 1em;
      }
      #extra > span {
        margin-left: 1ex;
        cursor: pointer;
      }
      x-icon {
        font-size: 22px;
        width: 22px;
        vertical-align: top;
      }
      .dropdown-caret {
        display: inline-block;
        width: 0;
        height: 0;
        vertical-align: middle;
        border-top-style: solid;
        border-top-width: 4px;
        border-right: 4px solid transparent;
        border-bottom: 0px solid transparent;
        border-left: 4px solid transparent;
      } 
    `;
  }
}
