import { customElement, LitElement, html, property, css } from 'lit-element';

@customElement('x-panel')
export class PanelElement extends LitElement {
  @property({type: String}) header = '';

  render() {
    return html`
      <div id="panel">
        <div id="title">${this.header}</div>
        <div id="contents"><slot></slot></div>
      </div>
    `
  }

  static get styles() {
    return css`
      #panel {
        border: 1px solid #ddd;
        border-radius: 8px;
      }
      #title {
        background-color: #f5f5f5;
        border-bottom: 1px solid #ddd;
        padding: 10px;
        padding-top: 0px;
        margin-top: 10px;
        font-size: 110%;
        font-weight: bold;
      }
      #contents {
        padding: 1em;
        display: flex;
      }
    `
  }
}
