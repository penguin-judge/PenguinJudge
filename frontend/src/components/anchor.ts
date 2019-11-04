import { router } from '../state';

export class AnchorElement extends HTMLAnchorElement {
  connectedCallback() {
    this.addEventListener("click", (e: MouseEvent) => {
      e.preventDefault();
      router.navigate(this.getAttribute('href'));
    });
  }
}

customElements.define('router-link', AnchorElement, { extends: 'a' });
