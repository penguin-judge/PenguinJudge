import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription, zip } from 'rxjs';
import { API, Submission } from '../api';
import { session } from '../state';
import { format_datetime_detail, getSubmittionStatusClass } from '../utils';

@customElement('penguin-judge-contest-submission')
export class PenguinJudgeContestSubmission extends LitElement {
  subscription: Subscription | null = null;
  submission: Submission | null = null;

  constructor() {
    super();
    this.subscription = zip(
      session.environment_mapping_subject,
      session.contest_subject
    ).subscribe(_ => {
      // ２つのsubjectが解決できれば
      // session.contest/session.environment_mapping経由でアクセスできる
      const s = session.contest;
      if (s) {
        const submission_id = location.hash.split('/').pop() || '';
        API.get_submission(s.id, submission_id).then((submission) => {
          this.submission = submission;
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
    if (!this.submission) {
      return;
    }
    const tests = this.submission.tests.map(
      t => html`<tr><td>${t.id}</td><td class="${getSubmittionStatusClass(t.status)}">${t.status}</td><td>${t.time === undefined ? '-' : t.time}</td><td>${t.memory === undefined ? '-' : t.memory}</td></tr>`);

    return html`
      <h2>提出: #${this.submission.id}</h2>
      <h3>ソースコード</h3>
      <pre>${this.submission.code}</pre>
      <h3>提出情報</h3>
      <table>
        <tr><th>提出日時</th><td>${format_datetime_detail(this.submission.created)}</td></tr>
        <tr><th>問題</th><td>${this.submission.problem_id}</td></tr>
        <tr><th>ユーザ</th><td>${this.submission.user_id}</td></tr>
        <tr><th>言語</th><td>${session.environment_mapping[this.submission.environment_id].name}</td></tr>
        <tr><th>結果</th><td class="${getSubmittionStatusClass(this.submission.status)}">${this.submission.status}</td></tr>
      </table>
      <h3>テストケース</h3>
      <table class="testcase">
        <thead>
          <tr><th>ケース名</th><th>結果</th><th>実行時間</th><th>メモリ</th></tr>
        </thead>
        <tbody>${tests}</tbody>
      </table>
    `;
  }

  static get styles() {
    return css`
      table {
        border-collapse:collapse;
      }
      td {
        border: 1px solid #bbb;
        padding: 0.5ex 1ex;
      }
      th {
        font-weight: bold;
      }
      table tr th {
        text-align: right;
      }
      thead th {
        text-align: center;
      }
      table.testcase tbody tr td:nth-child(3+n) {
        text-align: right;
      }
      .AC {
        background-color: #86C166;
      }
      .WA {
        background-color: #F05E1C;
      }  
    `;
  }
}
