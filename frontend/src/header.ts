import { customElement, LitElement, html, css } from 'lit-element';
import { HeaderHeight } from './consts';
import { router, session } from './state';

@customElement('x-header')
export class HeaderElement extends LitElement {
  constructor() {
    super();
    session.contest_subject.subscribe(_ => {
      this.requestUpdate();
    });
  }

  render() {
    const menus = [];
    if (session.contest) {
      menus.push(html`<li><x-anchor style="font-weight: bold" href="${router.generate('contest-top', {id: session.contest.id})}">${session.contest.title}</x-anchor></li>`);
      menus.push(html`<li><x-anchor href="${router.generate('contest-tasks', {id: session.contest.id})}">問題</x-anchor></li>`);
    } else {
      menus.push(html`<li><x-anchor href="${router.generate('home')}">ホーム</x-anchor></li>`);
      menus.push(html`<li><x-anchor href="${router.generate('contests')}">コンテスト</x-anchor></li>`);
    }
    return html`
      <div id='header'>
        <x-anchor href="${router.generate('home')}" id="logo">PenguinJudge</x-anchor>
        <ul id="menu">${menus}</ul>
      </div>
    `;
  }

  static get styles() {
    return css`
    #header {
      color: #fff;
      background-color: #000;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: ${HeaderHeight};
      display: flex;
      font-size: 90%;
    }
    #header x-anchor {
      color: #bbb;
    }
    #header x-anchor:hover {
      color: #fff;
    }
    #logo {
      font-size: 150%;
      font-weight: bold;
      align-self: center;
      margin-left: 1ex;
      margin-bottom: 5px;
    }
    ul#menu {
      list-style: none;
      overflow: hidden;
      display: flex;
      padding: 0;
    }
    ul#menu li {
      margin-left: 1.5em;
    }
    `;
  } 
}
