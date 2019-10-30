import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription } from 'rxjs';
import { API, Submission } from '../api';
import { session } from '../state';
import { format_datetime_detail } from '../utils';

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
      nodes.push(html`<tr><td>${format_datetime_detail(s.created)}</td><td>${s.problem_id}</td><td>${s.user_id}</td><td>${s.environment_id}</td><td>${s.status}</td></tr>`);
    });
    return html`
      <table>
        <thead><tr><td>提出日時</td><td>問題</td><td>ユーザ</td><td>言語</td><td>結果</td></tr></thead>
        <tbody>${nodes}</tbody>
      </table>`;
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
