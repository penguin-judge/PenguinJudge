import { customElement, LitElement, html, property } from 'lit-element';

import { API } from './api';
import { router } from './state';

@customElement('x-contests')
export class AppContentsElement extends LitElement {
  @property({type: Object}) contests = html``;

  constructor() {
    super()
    API.list_contests().then((contests) => {
      const tmp: Array<Object> = [];
      contests.forEach((c) => {
        tmp.push(html`<li><x-anchor href="${router.generate('contest-top', {id: c.id})}">${c.title}</x-anchor></li>`);
      });
      this.contests = html`<ol>${tmp}</ol>`;
    });
  }

  render() {
    return html`<h1>コンテスト一覧</h1>${this.contests}`;
  }
}
