import { customElement, LitElement, html, css } from 'lit-element';

@customElement('x-dropdown-menu')
export class DropDownMenuElement extends LitElement {
  constructor() {
    super();
    document.documentElement.addEventListener('click', () => {
      this.style.visibility = 'hidden';
    });
    this.style.visibility = 'hidden';
  }

  render() {
    return html`<slot></slot>`;
  }

  _sumOffsetXY(e: HTMLElement): [number, number] {
    let x = e.offsetLeft;
    let y = e.offsetTop;
    if (e.offsetParent) {
      let [px, py] = this._sumOffsetXY(<HTMLElement>e.offsetParent);
      x += px;
      y += py;
    }
    return [x, y];
  }

  show(e: HTMLElement) {
    const [x, y] = this._sumOffsetXY(e);
    this.style.left = (x + e.offsetWidth - this.offsetWidth) + 'px';
    this.style.top = (y + e.offsetHeight + 5) + 'px';
    this.style.visibility = 'visible';
    this.focus();
  }

  static get styles() {
    return css`
    :host {
      position: absolute;
      outline: none;
      background-color: white;
      border: 1px solid darkgrey;
      border-radius: 5px;
      box-shadow: 0 3px 10px rgba(30, 30, 30, .3);
      display: flex;
      flex-direction: column;
      padding: 5px 0;
    }
    * {
      white-space: nowrap;
    }
    ::slotted(a) {
      text-align: left;
      padding: 0.5ex 1em;
    }
    ::slotted(a:hover) {
      background-color: #eee;
    }
    ::slotted(hr) {
      margin: 0;
      padding: 0;
      border: 0;
      border-top: 1px solid darkgrey;
    }
    `;
  }
}
