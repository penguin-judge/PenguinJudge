import { customElement, LitElement, html } from 'lit-element';

@customElement('x-home')
export class AppHomeElement extends LitElement {
  render() {
    return html`<h1>Home</h1><p>上のメニューまたは<x-anchor href="/contests">ここ</x-anchor>をクリックしてコンテスト一覧ページに移動してね</p>`
  }
}
