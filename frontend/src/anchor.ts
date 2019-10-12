import { customElement, LitElement, html, property } from 'lit-element';
import { router } from './state';

@customElement('x-anchor')
export class AnchorElement extends LitElement {
  @property({type: String}) href = '';

  render() {
    return html`
      <style>
        :host, :host(:hover) { color: #0000ee; }
        :host(:visited) { color: #551a8b; }
        a { color: inherit; text-decoration: none; }
        a:hover { color: inherit; text-decoration: underline; }
      </style>
      <a @click="${this.handle}" href="${this.href}"><slot></slot></a>`
  }

  handle(e: MouseEvent) {
    e.preventDefault();
    router.navigate(this.href);
  }
}
