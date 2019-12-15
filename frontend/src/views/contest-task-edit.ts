import { customElement, LitElement, html, css } from 'lit-element';
//import { API } from '../api';
//import { router, session } from '../state';

@customElement('x-contest-task-edit')
export class AppContestTaskEditElement extends LitElement {
  render() {
    return html`hello`;
  }

  static get styles() {
    return css`
    :host {
      margin-left: 1em;
    }
    h1 { font-size: large; }
    `
  }
}
