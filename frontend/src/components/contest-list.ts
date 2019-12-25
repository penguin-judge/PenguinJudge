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
    return html`<table><thead><tr><th>開始時刻</th><th>コンテスト名</th><th>制限時間</th></tr></thead><tbody>${elements}</tbody></table>`;
  }

  static get styles() {
    return css`
    table{
      border-collapse: collapse;
      border-spacing: 0;
      width: 100%;
    }

    table tr{
      border-bottom: solid 1px #DDDDDD;
      cursor: pointer;
    }

    table tr:hover{
      background-color: #f0f8ff;
    }

    table th,table td{
      text-align: center;
      width: 25%;
      padding: 12px 0;
    }
    `
  }
}
