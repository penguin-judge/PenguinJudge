import { customElement, LitElement, html, css } from 'lit-element';
import { API, Status } from '../api';
import { format_datetime_detail } from '../utils';

@customElement('x-admin-status')
export class AppAdminStatusElement extends LitElement {
  status: Status | null = null;

  constructor() {
    super();
    this.refresh();
  }

  refresh() {
    API.get_status().then(s => {
      this.status = s;
      this.requestUpdate();
    });
  }

  render() {
    if (this.status === null)
      return html``;
    const now = new Date().getTime();
    const worker_rows = this.status.workers.map(w => {
      const lc = new Date(w.last_contact);
      const ago = Math.round((now - lc.getTime()) / 1000);
      return html`<tr><td>${w.hostname}</td><td>${w.pid}</td>
        <td>${w.max_processes}</td>
        <td>${format_datetime_detail(w.startup_time)}</td>
        <td>${format_datetime_detail(lc)} (${ago}s ago)</td>
        <td>${w.processed}</td>
        <td>${w.errors}</td>
      </tr>`;
    });
    const worker_table = html`<table><thead><tr>
      <th>ホスト名</th>
      <th>pid</th>
      <th>CPUs</th>
      <th>起動日時</th>
      <th>最終コンタクト日時</th>
      <th>処理タスク数</th>
      <th>エラータスク数</th>
    </tr></thead><tbody>${worker_rows}</tbody></table>`;
    return html`
      <div id="container">
        <x-panel header="Queued"><div class="contents">${this.status.queued}</div></x-panel>
        <div class="item"><button @click="${this.refresh}"><x-icon>refresh</x-icon></button></div>
      </div>
      <x-panel header="Workers">${worker_table}</x-panel>`;
  }

  static get styles() {
    return css`
    :host { display: flex; margin: 1em; flex-direction: column; }
    #container { display: flex; justify-content: space-between; margin-bottom: 1em}
    .item { margin-right: 1em; }
    div.contents { text-align: center; flex-grow: 1; font-size: x-large; font-weight: bold; }
    table { border-collapse: collapse; border-spacing: 0; border-radius: 2px; }
    td, th { padding: 0.7ex 1ex; white-space: nowrap; }
    tbody tr:nth-child(odd) { background: #f5f5f5; }
    td, th { border: 1px solid #ccc; }
    button {
      font-size: 32px;
      padding: 0.2em 0.3em 0 0.3em;
      margin: 0;
      border: solid 2px #aaa;
      border-radius: 3px;
      cursor: pointer;
    }
    `;
  }
}
