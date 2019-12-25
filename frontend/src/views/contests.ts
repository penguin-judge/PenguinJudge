import { customElement, LitElement, html, css } from 'lit-element';

import { API, Contest } from '../api';
import { MainAreaPaddingPx } from './consts';
import { ContestListElement } from '../components/contest-list';

@customElement('x-contests')
export class AppContentsElement extends LitElement {
  _table = new ContestListElement();
  _contests: Contest[] = [];

  constructor() {
    super()
    API.list_contests().then(contests => {
      this._contests = contests;
      this.requestUpdate();
    });
  }

  render() {
    this._table.setItems(this._contests);
    return html`<h2>コンテスト一覧</h2>${this._table}`;
  }

  static get styles() {
    return css`
      :host {
        display: flex;
        flex-direction: column;
        padding: ${MainAreaPaddingPx}px;
      }
    `
  }
}
