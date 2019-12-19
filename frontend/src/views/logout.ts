import { customElement, LitElement, html, css } from 'lit-element';
import { MainAreaPaddingPx } from './consts';
import { session } from '../state';

@customElement('x-logout')
export class PenguinJudgeLogoutElement extends LitElement {
  constructor() {
    super();
    session.delete_current_user();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
  }

  render() {
    return html`
      <x-panel header="">
        <div>ログアウトしました</div>
      </x-panel>
    `
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
