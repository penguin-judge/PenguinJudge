import Marked from 'marked';
import { customElement, LitElement, property, html, css, unsafeCSS } from 'lit-element';
import { unsafeHTML } from 'lit-html/directives/unsafe-html.js';

// @ts-ignore
import renderMathInElement from 'katex/contrib/auto-render/auto-render';

const katex_css = require('katex/dist/katex.min.css').toString();

@customElement('x-markdown')
export class MarkdownElement extends LitElement {
  @property({type: String})
  value = '';

  render() {
    return html`${unsafeHTML(Marked(this.value))}`;
  }

  updated() {
    if (this.shadowRoot === null)
      return;
    const config = {
      delimiters: [
        {left: '$', right: '$', display: false},
        {left: '\[', right: '\]', display: true}
      ],
      output: 'html',
    };
    renderMathInElement(this.shadowRoot, config);
  }

  static get styles() {
    return css`
    :host {
      display: block;
    }
    pre {
      padding: 1em;
      border: 1px solid #ccc;
      background-color: #fff;
    }
    pre code {
      padding: 0;
    }
    code {
      padding: 0.5ex;
      background-color: #fff;
    }
    span:not(.katex-display) > span.katex {
      margin: 0 0.2em;
    }
    ${unsafeCSS(katex_css)}
    `;
  }
}
