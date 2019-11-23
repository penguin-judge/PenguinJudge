import { customElement, LitElement, html, css, TemplateResult } from 'lit-element';
import { Contest } from '../api';
import { router } from '../state';
import { format_datetime, format_timespan } from '../utils';

@customElement('x-contest-list')
export class ContestListElement extends LitElement {
  _items: Contest[] = [];

  public setItems(items: Contest[]) {
    this._items = items;
    this.requestUpdate();
  }

  render() {
    const elements: TemplateResult[] = [];
    this._items.forEach(c => {
      const href= router.generate('contest-top', { id: c.id });
      elements.push(html`<tr @click="${() => router.navigate(href)}">
        <td><a is="router-link" href="${href}">${format_datetime(c.start_time)}</a></td>
        <td><a is="router-link" href="${href}">${c.title}</a></td>
        <td>${format_timespan(Date.parse(c.end_time) - Date.parse(c.start_time))}</td>
      </tr>`);
    });
    return html`<table><thead><tr><th>開始時刻</th><th>コンテスト名</th><th>時間</th></tr></thead><tbody>${elements}</tbody></table>`;
  }

  static get styles() {
    return css`
    table { width: 100%; border-collapse: collapse; border-spacing: 0; border-radius: 2px; }
    td, th { padding: 0.7ex 1ex; white-space: nowrap; }
    thead th:nth-child(2) { text-align: left; padding-left: 1ex; }
    td:nth-child(2) { width: 100%; white-space: normal; }
    tbody tr:nth-child(odd) { background: #f5f5f5; }
    td, th { border: 1px solid #ccc; }
    tbody tr:hover { background-color: #f0f0f0; cursor: pointer; }
    `
  }
}
