import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription, merge } from 'rxjs';
import { API, Submission } from '../api';
import { router, session } from '../state';
import { format_datetime_detail, getSubmittionStatusMark } from '../utils';

@customElement('penguin-judge-contest-submission-results')
export class PenguinJudgeContestSubmissionResults extends LitElement {
  subscription: Subscription | null = null;
  submissions: Submission[] = [];
  number_of_pages = 1;
  page_index = 1;

  constructor() {
    super();
    this.subscription = merge(
      session.environment_mapping_subject,
      session.contest_subject,
    ).subscribe(_ => {
      // ２つのsubjectが解決できれば
      // session.contest/session.environment_mapping経由でアクセスできる
      if (session.contest && session.environments) {
        this.loadSubmissions();
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

  changePage(e: CustomEvent) {
    this.page_index = e.detail;
    this.loadSubmissions();
  }

  loadSubmissions() {
    API.list_submissions(session.contest!.id, this.page_index).then(([submissions, resp]) => {
      const x_total_pages = resp.headers.get('x-total-pages');
      if (x_total_pages)
        this.number_of_pages = parseInt(x_total_pages);
      this.submissions = submissions;
      this.requestUpdate();
    }, _ => {});
  }

  render() {
    if (!session.contest) {
      return html``;
    }
    if (!session.contest.problems) {
      return html`<div>コンテスト開催前です</div>`;
    }

    let pagenation;
    if (this.number_of_pages >= 1)
      pagenation = html`<penguin-judge-pagenation pages="${this.number_of_pages}" currentPage="${this.page_index}" @page-changed="${this.changePage}"></penguin-judge-pagenation>`;

    const nodes = this.submissions.map(s => {
      const url = router.generate('contest-submission', { id: session.contest!.id, submission_id: s.id });
      return html`
        <tr>
          <td>${format_datetime_detail(s.created)}</td>
          <td><a is="router_link" href="${router.generate('contest-task', { id: session.contest!.id, task_id: [s.problem_id] })}">${[s.problem_id]}</a></td>
          <td>${s.user_id}</td>
          <td>${session.environment_mapping[s.environment_id].name}</td>
          <td>${getSubmittionStatusMark(s.status)}${s.status}</td>
          <td><a is="router_link" href="${url}">詳細</td>
        </tr>`;
    });
    return html`
      ${pagenation}
      <table>
        <thead><tr><td>提出日時</td><td>問題</td><td>ユーザ</td><td>言語</td><td>結果</td><td></td></tr></thead>
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
    .AC {
      color: green;
    }
    .WA {
      color: red;
    }
    `;
  }
}
