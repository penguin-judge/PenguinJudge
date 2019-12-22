import { customElement, LitElement, html, css } from 'lit-element';
import { MainAreaPaddingPx } from './consts';
import { session } from '../state';

@customElement('x-logout')
export class PenguinJudgeLogoutElement extends LitElement {
  inflight = true;
  error = undefined;

  constructor() {
    super();
    session.logout().catch(e => {
      this.error = e;
    }).finally(() => {
      this.inflight = false;
      this.requestUpdate();
    });
  }

  render() {
    let contents;
    if (this.inflight) {
      contents = html`<div>ログアウト中</div>`;
    } else {
      if (this.error) {
        contents = html`<div>ログアウト処理に失敗しました</div>`;
      } else {
        contents = html`<div>ログアウトしました</div>`;
      }
    }
    return html`<x-panel header="">${contents}</x-panel>`;
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
    `;
  }
}
