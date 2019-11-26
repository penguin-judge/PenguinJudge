import { customElement, LitElement, html, css } from 'lit-element';

import { API, Contest } from '../api';
import { MainAreaPaddingPx } from './consts';
import { ContestListElement } from '../components/contest-list';
import { session } from '../state';
import { check_contest_status } from '../utils';

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
    if (!session.contest)
      return html`?`;

    if(check_contest_status(session.contest.start_time, session.contest.end_time) == 'scheduled')
      return html`コンテスト開催前です`;

    this._table.setItems(this._contests);
    return html`${this._table}`;
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
