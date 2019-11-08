import { router } from '../state';

export class AnchorElement extends HTMLAnchorElement {
  connectedCallback() {
    this.addEventListener("click", (e: MouseEvent) => {
      (<HTMLElement>e.target).blur();
      e.preventDefault();
      router.navigate(this.getAttribute('href'));
    });
  }
}

customElements.define('router-link', AnchorElement, { extends: 'a' });
