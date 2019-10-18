import { customElement, LitElement, html, property } from 'lit-element';
import { router } from '../state';

@customElement('x-anchor')
export class AnchorElement extends LitElement {
  @property({type: String}) href = '';

  render() {
    return html`<a @click="${this.handle}" href="${this.href}"><slot></slot></a>`
  }

  handle(e: MouseEvent) {
    e.preventDefault();
    router.navigate(this.href);
  }
}
