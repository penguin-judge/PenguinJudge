import { customElement, LitElement, html, property, css } from 'lit-element';

import { API } from './api';
import { MainAreaPaddingPx } from './consts';
import { router } from './state';
import { format_datetime, format_timespan } from './utils';

@customElement('x-contests')
export class AppContentsElement extends LitElement {
  @property({type: Object}) contests = html``;

  constructor() {
    super()
    API.list_contests().then((contests) => {
      const tmp: Array<Object> = [];
      contests.forEach((c) => {
        tmp.push(html`<tr>
          <td>${format_datetime(c.start_time)}</td>
          <td><x-anchor href="${router.generate('contest-top', {id: c.id})}">${c.title}</x-anchor></td>
          <td>${format_timespan(Date.parse(c.end_time) - Date.parse(c.start_time))}</td>
        </tr>`);
      });
      this.contests = html`
        <table><thead><tr><td>開始時刻</td><td>コンテスト名</td><td>時間</td></tr></thead>
        <tbody>${tmp}</tbody></table>`;
    });
  }

  render() {
    return html`
      <x-panel header="開催中のコンテスト">
        ${this.contests}
      </x-panel>
      <x-panel header="開催予定のコンテスト">
        <div>ほげほげ</div>
      </x-panel>
      <x-panel header="終了したコンテスト">
        <div>ほげほげ</div>
      </x-panel>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: flex;
        flex-direction: column;
        padding: ${MainAreaPaddingPx}px;
      }
      x-panel {
        margin-bottom: 20px;
      }
    `
  }
}
