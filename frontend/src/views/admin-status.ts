import { Subscription, timer } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { API, Status } from '../api';

@customElement('x-admin-status')
export class AppAdminStatusElement extends LitElement {
  subscription : Subscription | null = null;
  status: Status | null = null;

  constructor() {
    super();
    this.subscription = timer(0, 1000).subscribe(_ => {
      API.get_status().then(s => {
        this.status = s;
        this.requestUpdate();
      });
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.subscription) {
      this.subscription.unsubscribe();
      this.subscription = null;
    }
  }

  render() {
    if (this.status === null)
      return html``;
    return html`<x-panel header="Queued"><div>${this.status.queued}</div></x-panel>`;
  }

  static get styles() {
    return css`
    :host { display: flex; flex-wrap: wrap; margin: 1em; }
    div { text-align: center; flex-grow: 1; font-size: x-large; font-weight: bold; }
    `;
  }
}
