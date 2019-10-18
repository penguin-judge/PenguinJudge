import { customElement, LitElement, html, css } from 'lit-element';
import { MainAreaPaddingPx } from './consts';

@customElement('x-home')
export class AppHomeElement extends LitElement {
  render() {
    return html`
      <x-panel header="お知らせ">
        <div>特になさそう</div>
      </x-panel>
      <x-panel header="最近のコンテスト">
        <div>ほげほげ</div>
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
