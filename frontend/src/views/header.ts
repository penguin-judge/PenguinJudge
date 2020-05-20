import { customElement, LitElement, html, css, unsafeCSS } from 'lit-element';
import { HeaderHeight, HeaderHeightPx } from './consts';
import { router, session } from '../state';
import { DropDownMenuElement } from '../components/dropdown-menu';

@customElement('penguin-judge-header')
export class PenguinJudgeHeaderElement extends LitElement {
  showToolbar = false;
  enableUserCreationLink = false;

  constructor() {
    super();
    session.contest_subject.subscribe(_ => {
      this.requestUpdate();
    });
    session.current_user.subscribe(_ => {
      this.requestUpdate();
    });
    session.environment_subject.subscribe(envs => {
      // HACK: 環境が取得できていればアカウントの作成が有効
      this.enableUserCreationLink = (envs !== null);
      this.showToolbar = this.enableUserCreationLink;
      this.requestUpdate();
    });
  }

  showMenu(e: MouseEvent) {
    e.preventDefault();
    e.stopImmediatePropagation();
    const menu = <DropDownMenuElement>this.shadowRoot!.querySelector('x-dropdown-menu');
    if (menu && e.currentTarget) {
      menu.show(<HTMLElement>e.currentTarget);
    }
  }

  render() {
    let title = 'Penguin Judge';
    let title_link = router.generate('home');
    if (session.contest) {
      title = session.contest.title;
      title_link = router.generate('contest-top', { id: session.contest.id });
    }

    let admin_area, user_area;
    let is_admin = false;
    let menus = [];
    if (session.current_user.value) {
      is_admin = session.current_user.value.admin;
      menus.push(html`<a is="router-link" href="${router.generate('profile')}">プロフィール</b>`);
      menus.push(html`<a is="router-link" href="${router.generate('logout')}">ログアウト</b>`);
      if (is_admin) {
        menus.push(html`<hr>`);
        menus.push(html`<a is="router-link" href="${router.generate('admin-status')}">システムの状態</a>`);
        menus.push(html`<a is="router-link" href="${router.generate('admin-environments')}">言語環境の設定</a>`);
      }
      user_area = html`<span tabindex="0" @click="${this.showMenu}">
        <x-icon>person</x-icon>
        <span>${session.current_user.value.name}</span>
        <span class="dropdown-caret"></span>
      </span>`;
      if (is_admin) {
        admin_area = html`
          <span tabindex="0">
            <a is="router-link" href="${router.generate('contest-new')}" title="新規コンテスト">
              <x-icon>add</x-icon>
            </a>
          </span>
        `;
      }
    } else {
      user_area = html`
        ${this.enableUserCreationLink ? html`<span><a is="router-link" href="${router.generate('register')}">登録</a></span>` : html``}
        <span><a is="router-link" href="${router.generate('login')}">ログイン</a></span>
      `
    }
    return html`
      <span id="icon-area">
        <a is="router-link" href="${router.generate('home')}"><img id="icon" src="/images/penguin.png"></a>
      </span>
      <span id="title">
        <a href="${title_link}" is="router-link">${title}</a>
      </span>
      <span id="extra">
        ${admin_area}${this.showToolbar ? html`
        <span tabindex="0">
          <a is="router-link" href="${router.generate('home')}" title="ホームに戻る">
            <x-icon>home</x-icon>
          </a>
        </span>
        <span tabindex="0">
          <a is="router-link" href="${router.generate('contests')}" title="コンテスト一覧">
            <x-icon>insert_chart_outlined</x-icon>
          </a>
        </span>` : html``}
        ${user_area}
      </span>
      <x-dropdown-menu tabindex="0">${menus}</x-dropdown-menu>
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
