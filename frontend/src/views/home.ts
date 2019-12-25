import { customElement, LitElement, html, css } from 'lit-element';
import { API, Contest } from '../api';
import { ContestListElement } from '../components/contest-list';
import { MainAreaPaddingPx } from './consts';

@customElement('x-home')
export class AppHomeElement extends LitElement {
  _runnings: Array<Contest> = [];
  _scheduleds: Array<Contest> = [];
  _finisheds: Array<Contest> = [];

  constructor() {
    super();
    API.list_contests().then(contests => {
      this._runnings = [];
      this._scheduleds = [];
      this._finisheds = [];
      const now = new Date();
      contests.forEach(c => {
        const s = new Date(c.start_time);
        const e = new Date(c.end_time);
        if (s <= now && now < e) {
          this._runnings.push(c);
        } else if (now < s) {
          this._scheduleds.push(c);
        } else {
          this._finisheds.push(c);
        }
      });
      this.requestUpdate();
    });
  }

  render() {
    const panels: Array<any> = [];
    const build_table = (title: string, contests: Array<Contest>) => {
      const body = (() => {
        if (contests.length > 0) {
          const table = new ContestListElement();
          table.setItems(contests);
          return table;
        } else {
          return html`とくにありません`;
        }
      })();
      panels.push(html`<x-panel header="${title}">${body}</x-panel>`);
    };
    panels.push(html`<x-panel header="Welcome!"><div>ようこそ！<br>コーディングチャレンジ2019です。</div></x-panel>`);
    build_table('開催中のコンテスト', this._runnings);
    build_table('開催予定のコンテスト', this._scheduleds);
    build_table('終了したコンテスト', this._finisheds);
    return html`${panels}`;
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
      x-contest-list {
        flex-grow: 1;
      }
    `
  }
}
