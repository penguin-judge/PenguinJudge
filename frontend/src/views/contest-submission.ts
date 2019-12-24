import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription, merge } from 'rxjs';
import { API, Submission } from '../api';
import { router, session } from '../state';
import { format_datetime_detail, getSubmittionStatusMark } from '../utils';
import { AceEditor } from '../components/ace';

@customElement('penguin-judge-contest-submission')
export class PenguinJudgeContestSubmission extends LitElement {
  subscription: Subscription | null = null;
  submission: Submission | null = null;

  constructor() {
    super();
    this.subscription = merge(
      session.environment_mapping_subject,
      session.contest_subject
    ).subscribe(_ => {
      // ２つのsubjectが解決できれば
      // session.contest/session.environment_mapping経由でアクセスできる
      const s = session.contest;
      if (s && session.environments) {
        const submission_id = location.hash.split('/').pop() || '';
        API.get_submission(s.id, submission_id).then((submission) => {
          this.submission = submission;
          this.requestUpdate();
        });
      }
    });
    this.updateComplete.then(() => {
      this.updated(null);
    });
  }

  updated(changedProperties: any) {
    if (changedProperties !== null)
      super.updated(changedProperties);
    const code = <AceEditor>this.shadowRoot!.getElementById("code");
    if (code && code.editor && this.submission) {
      code.editor.setReadOnly(true);
      code.editor.setValue(this.submission.code, -1);
      code.setModeFromAmbiguous(session.environment_mapping[this.submission.environment_id].name);
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.subscription) {
      this.subscription.unsubscribe();
      this.subscription = null;
    }
  }

  render() {
    if (!this.submission) {
      return html``;
    }
    const tests = this.submission.tests.map(
      t => html`
        <tr>
          <td>${t.id}</td>
          <td>${getSubmittionStatusMark(t.status)}${t.status}</td>
          <td>${t.time === undefined ? '-' : `${Math.ceil(t.time! * 1000)} msec`}</td>
          <td>${t.memory === undefined ? '-' : `${Math.ceil(t.memory! / 1000)} MB`}</td>
        </tr>
      `);
    let problem_title = this.submission.problem_id;
    if (session.contest && session.contest.problems) {
      const p = session!.contest!.problems!.find(p => p.id === this.submission!.problem_id);
      if (p)
        problem_title = p.title;
    }
    return html`
      <h2>提出: #${this.submission.id} <span>${getSubmittionStatusMark(this.submission.status)}${this.submission.status}</span></h2>
      <div id="container">
        <div id="left-pane">
          <div class="info">
            <div>
              <label>提出日時:</label>
              <span>${format_datetime_detail(this.submission.created)}</span>
            </div>
            <div>
              <label>問題:</label>
              <span><a is="router_link" href="${router.generate('contest-task', { id: session.contest!.id, task_id: this.submission.problem_id })}">${problem_title}</a></span>
            </div>
            <div>
              <label>言語:</label>
              <span>${session.environment_mapping[this.submission.environment_id].name}</span>
            </div>
            <div>
              <label>ユーザー:</label>
              <span>${this.submission.user_id}</span>
            </div>
          </div>
          <h3>ソースコード</h3>
          <x-ace-editor id="code"></x-ace-editor>
        </div>
        <div id="right-pane">
          <h3>テストケース</h3>
          <div>
            <table class="testcase">
              <thead><tr><th>#</th><th>結果</th><th>実行時間</th><th>メモリ</th></tr></thead>
              <tbody>${tests}</tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: flex;
        flex-direction: column;
      }
      #container {
        flex-grow: 1;
        display: flex;
      }
      h2 { margin: 0; font-size: x-large; }
      h2 span { vertical-align: middle; }
      h3 { margin: 1ex 0; }
      #left-pane {
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        margin-right: 2em;
      }
      #code {
        flex-grow: 1;
      }

      .info {
        margin: 1ex 0;
        display: flex;
        flex-wrap: wrap;
      }
      .info > div {
        margin-right: 1em;
        white-space: nowrap;
      }
      .info label {
        font-weight: bold;
      }

      table {
        border-collapse:collapse;
      }
      td {
        border: 1px solid #bbb;
        padding: 0.8ex 1ex;
        white-space: nowrap;
      }
      th {
        font-weight: bold;
        text-align: center;
      }
      .testcase td:nth-child(n+3) {
        text-align: right;
      }
      td .AC, td.WA { margin-right: 2px }
      .AC, .WA { vertical-align: middle; }
      .AC {
        color: green;
      }
      .WA {
        color: red;
      }
    `;
  }
}
