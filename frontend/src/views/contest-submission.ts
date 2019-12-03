import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription } from 'rxjs';
import { API, Submission } from '../api';
import { session } from '../state';
import { format_datetime_detail } from '../utils';

@customElement('penguin-judge-contest-submission')
export class PenguinJudgeContestSubmission extends LitElement {
  subscription: Subscription | null = null;
  submission: Submission | null = null;

  constructor() {
    super();
    this.subscription = session.contest_subject.subscribe((s) => {
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
    return html`
      <h2>提出: #${this.submission.id}</h2>
      <h3>ソースコード</h3>
      <pre>${this.submission.code}</pre>
      <h3>提出情報</h3>
      <table>
        <tbody><td>提出日時</td><td>${format_datetime_detail(this.submission.created)}</td></tbody>
        <tbody><td>問題</td><td>${this.submission.problem_id}</td></tbody>
        <tbody><td>ユーザ</td><td>${this.submission.user_id}</td></tbody>
        <tbody><td>言語</td><td>${this.submission.environment_id}</td></tbody>
        <tbody><td>結果</td><td>${this.submission.status}</td></tbody>
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
    thead td {
      font-weight: bold;
      text-align: center;
    }
    `;
  }
}
