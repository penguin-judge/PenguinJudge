import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription } from 'rxjs';
import { API, Submission } from './api';
import { session } from './state';
import { format_datetime_detail } from './utils';

import { BsContentRebootCss, BsContentTypographyCss } from '@lit-element-bootstrap/content';
import { BsTextCss, BsTextColorCss, BsSpacingCss, BsDisplayCss } from '@lit-element-bootstrap/utilities';
import { BsFlexDisplayCss,
    BsFlexJustifyCss,
    BsFlexWrapCss,
    BsFlexAlignContentCss,
    BsFlexDirectionCss,
    BsFlexOrderCss, BsBackgroundColorsCss, BsBordersCss } from '@lit-element-bootstrap/utilities';

@customElement('penguin-judge-contest-submission-results')
export class PenguinJudgeContestSubmissionResults extends LitElement {
  subscription: Subscription | null = null;
  submissions: Submission[] = [];

  constructor() {
    super();
    this.subscription = session.contest_subject.subscribe((s) => {
      if (s) {
        API.list_own_submissions(s.id).then((submissions) => {
          this.submissions = submissions;
          this.requestUpdate();
        });
      }
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
    const nodes: any[] = [];
    this.submissions.forEach((s) => {
      nodes.push(html`
        <bs-row>
          <bs-column sm-2 demo class="border">${format_datetime_detail(s.created)}</bs-column>
          <bs-column sm-2 demo class="border">${s.problem_id}</bs-column>
          <bs-column sm-3 demo class="border">${s.user_id}</bs-column>
          <bs-column sm-2 demo class="border">${s.environment_id}</bs-column>
          <bs-column sm-3 demo class="border">${s.status}</bs-column>
        </bs-row>`);
    });
    return html`
    <bs-container>
      <bs-row>
        <bs-column><br></bs-column>
      </bs-row>
      <bs-row style="background-color:#CCE5FF;">
        <bs-column sm-2 demo class="border text-dark">
        提出日時
        </bs-column>
        <bs-column sm-2 demo class="border text-dark">
        問題
        </bs-column>
        <bs-column sm-3 demo class="border text-dark">
        ユーザ
        </bs-column>
        <bs-column sm-2 demo class="border text-dark">
        言語
        </bs-column>
        <bs-column sm-3 demo class="border text-dark">
        結果
        </bs-column>
      </bs-row>
      ${nodes}
    </bs-container>`;
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

}
