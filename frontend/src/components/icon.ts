import { customElement, LitElement, html, property, css } from 'lit-element';

@customElement('x-icon')
export class IconElement extends LitElement {
  @property({type: String}) key = '';

  render() {
    return html`<i>${this.key}</i>`
  }

  static get styles() {
    return css`
      i {
        font-family: 'Material Icons';
        font-weight: normal;
        font-style: normal;
        font-size: inherit;
        display: inline-block;
        line-height: 1;
        text-transform: none;
        letter-spacing: normal;
        word-wrap: normal;
        white-space: nowrap;
        direction: ltr;
        /* Support for all WebKit browsers. */
        -webkit-font-smoothing: antialiased;
        /* Support for Safari and Chrome. */
        text-rendering: optimizeLegibility;
        /* Support for Firefox. */
        -moz-osx-font-smoothing: grayscale;
        /* Support for IE. */
        font-feature-settings: 'liga';
        width: inherit;
        height: inherit;
      }
      i, i:link, i:hover, i:visited, i:active {
        color: inherit;
      }
    `
  }
}
