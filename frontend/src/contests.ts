import { customElement, LitElement, html, property, css } from 'lit-element';
import { BsContentRebootCss, BsContentTypographyCss } from '@lit-element-bootstrap/content';
import { BsTextCss, BsTextColorCss, BsSpacingCss, BsDisplayCss } from '@lit-element-bootstrap/utilities';
import { BsFlexDisplayCss,
    BsFlexJustifyCss,
    BsFlexWrapCss,
    BsFlexAlignContentCss,
    BsFlexDirectionCss,
    BsFlexOrderCss, BsBackgroundColorsCss, BsBordersCss } from '@lit-element-bootstrap/utilities';

import { API } from './api';
//import { MainAreaPaddingPx } from './consts';
import { router } from './state';
import { format_datetime, format_timespan } from './utils';

@customElement('x-contests')
export class AppContentsElement extends LitElement {
  @property({type: Object}) contests = html``;

  constructor() {
    super()
    API.list_contests().then((contests) => {
      const tmp: Array<Object> = [];
      contests.forEach((c) => {
        tmp.push(html`<bs-row>
          <bs-column sm-3 demo class="border">${format_datetime(c.start_time)}</bs-column>
          <bs-column sm-6 demo class="border"><x-anchor href="${router.generate('contest-top', {id: c.id})}">${c.title}</x-anchor></bs-column>
          <bs-column sm-3 demo class="border">${format_timespan(Date.parse(c.end_time) - Date.parse(c.start_time))}</bs-column>
        </bs-row>`);
      });
      this.contests = html`
        ${tmp}
        `;
    });
  }

  render() {
    return html`
    <bs-container>
        <bs-row>
            <bs-column sm-12 demo>
            <bs-card>
                <bs-card-header slot="card-header">開催中のコンテスト</bs-card-header>
                <bs-card-body>
                  <bs-container>
                    <bs-row style="background-color:#CCE5FF;" class="text-dark">
                      <bs-column sm-3 demo class="border">
                      開始時刻
                      </bs-column>
                      <bs-column sm-6 demo class="border">
                      コンテスト名
                      </bs-column>
                      <bs-column sm-3 demo class="border">
                      時間
                      </bs-column>
                    </bs-row>
                    ${this.contests}
                  </bs-container>
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
                <bs-card-header slot="card-header">開催予定のコンテスト</bs-card-header>
                <bs-card-body>
                    <bs-card-text slot="card-text">
                        <p>ほげほげ</p>
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
                <bs-card-header slot="card-header">終了したコンテスト</bs-card-header>
                <bs-card-body>
                    <bs-card-text slot="card-text">
                        <p>ほげほげ</p>
                    </bs-card-text>
                </bs-card-body>
            </bs-card>
            </bs-column>
        </bs-row>
    </bs-container>
    `;
  }

  static get styles() {
        return [
            BsContentRebootCss,
            BsContentTypographyCss,
            BsBordersCss,
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

//  static get styles() {
//    return css`
//      :host {
//        display: flex;
//        flex-direction: column;
//        padding: ${MainAreaPaddingPx}px;
//      }
//      x-panel {
//        margin-bottom: 20px;
//      }
//    `
//  }
}
