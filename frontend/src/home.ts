import { customElement, LitElement, html, css } from 'lit-element';

import { BsContentRebootCss, BsContentTypographyCss } from '@lit-element-bootstrap/content';
import { BsTextCss, BsTextColorCss, BsSpacingCss, BsDisplayCss } from '@lit-element-bootstrap/utilities';
import { BsFlexDisplayCss,
    BsFlexJustifyCss,
    BsFlexWrapCss,
    BsFlexAlignContentCss,
    BsFlexDirectionCss,
    BsFlexOrderCss, BsBackgroundColorsCss } from '@lit-element-bootstrap/utilities';

@customElement('x-home')
export class AppHomeElement extends LitElement {
  render() {
    return html`
    <bs-container>
        <bs-row>
            <bs-column sm-12 demo>
            <bs-card>
                <bs-card-header slot="card-header">お知らせ</bs-card-header>
                <bs-card-body>
                    <bs-card-text slot="card-text">
                        <p>特になさそう</p>
                    </bs-card-text>
                </bs-card-body>
            </bs-card>
            </bs-column>
        </bs-row>
        <bs-row>
          <bs-column sm-12 demo><br></bs-column>
        </bs-row>
        <bs-row>
            <bs-column sm-12 demo>
            <bs-card>
                <bs-card-header slot="card-header">最近のコンテスト</bs-card-header>
                <bs-card-body>
                    <bs-card-text slot="card-text">
                        <p>ほげほげ</p>
                    </bs-card-text>
                </bs-card-body>
            </bs-card>
            </bs-column>
        </bs-row>
    </bs-container>
    `
  }

  static get styles() {
        return [
            BsContentRebootCss,
            BsContentTypographyCss,
            BsTextCss,
            BsTextColorCss,
            BsDisplayCss,
            BsFlexWrapCss,
            BsFlexOrderCss,
            BsFlexDisplayCss,
            BsFlexDirectionCss,
            BsFlexJustifyCss,
            BsSpacingCss,
            BsFlexAlignContentCss,
            BsBackgroundColorsCss,
            css`
                bs-jumbotron {
                    margin-top: 15px;
                }
                div#jumbotron-buttons {
                    margin-bottom: 20px;
                }
                div#jumbotron-buttons bs-link-button {
                    margin-right: 20px;
                }
            `
        ];
    }
}
