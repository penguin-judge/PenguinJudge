import { Subscription } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { router, session } from './state';

import { BsContentRebootCss, BsContentTypographyCss } from '@lit-element-bootstrap/content';
import { BsTextCss, BsTextColorCss, BsSpacingCss, BsDisplayCss } from '@lit-element-bootstrap/utilities';
import { BsFlexDisplayCss,
    BsFlexJustifyCss,
    BsFlexWrapCss,
    BsFlexAlignContentCss,
    BsFlexDirectionCss,
    BsFlexOrderCss, BsBackgroundColorsCss, BsBordersCss } from '@lit-element-bootstrap/utilities';

@customElement('x-contest-tasks')
export class AppContestTasksElement extends LitElement {
  subscription: Subscription | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.subscription = session.contest_subject.subscribe(_ => {
      this.requestUpdate();
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.subscription) {
      this.subscription.unsubscribe();
      this.subscription = null;
    }
  }

  render() {
    const dom_problems: Array<Object> = [];
    if (session.contest && session.contest.problems) {
      const contest_id = session.contest.id;
      session.contest.problems.forEach((problem) => {
        const url = router.generate('contest-task', {id: contest_id, task_id: problem.id});
      /*  dom_problems.push(html`<tr>
                          <td><x-anchor href="${url}">${problem.id}</td>
                          <td><x-anchor href="${url}">${problem.title}</td></tr>`);*/
        dom_problems.push(html`<bs-row>
          <bs-column sm-1 demo class="border"><x-anchor href="${url}">${problem.id}</bs-column>
          <bs-column sm-5 demo class="border"><x-anchor href="${url}">${problem.title}</bs-column>
          <bs-column sm-4 demo class="border">メモリ:1024M / 時間2Sec</bs-column>
          <bs-column sm-2 demo class="border">100点</bs-column>
        </bs-row>`);
      });
    }
    return html`
        <bs-container>
          <bs-row>
            <bs-column><br></bs-column>
          </bs-row>
          <bs-row>
              <bs-column sm-12 demo>
              <bs-card>
                  <bs-card-header slot="card-header">問題</bs-card-header>
                  <bs-card-body>
                    <bs-container>
                      <bs-row style="background-color:#CCE5FF;">
                        <bs-column sm-1 demo class="border text-dark">
                        ID
                        </bs-column>
                        <bs-column sm-5 demo class="border text-dark">
                        問題名
                        </bs-column>
                        <bs-column sm-4 demo class="border text-dark">
                        制限
                        </bs-column>
                        <bs-column sm-2 demo class="border text-dark">
                        配点
                        </bs-column>
                      </bs-row>
                      ${dom_problems}
                    </bs-container>
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
//    table {
//      border-collapse: collapse;
//    }
//    th, td {
//      border: solid 1px #ddd;
//      padding: 1ex 2ex;
//      text-align: left;
//    }
//    tbody tr:nth-child(odd) {
//      background-color: #f1f1f1;
//    }
//    `
//  }
}
