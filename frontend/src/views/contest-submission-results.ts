import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription, zip } from 'rxjs';
import { API, Submission } from '../api';
import { router, session } from '../state';
import { format_datetime_detail, getSubmittionStatusMark } from '../utils';

@customElement('penguin-judge-contest-submission-results')
export class PenguinJudgeContestSubmissionResults extends LitElement {
  subscription: Subscription | null = null;
  submissions: Submission[] = [];
  page: number = 1;
  contestId: string | null = null;

  constructor() {
    super();
    this.subscription = zip(
      session.environment_mapping_subject,
      session.contest_subject,
    ).subscribe(_ => {
      // ２つのsubjectが解決できれば
      // session.contest/session.environment_mapping経由でアクセスできる
      const s = session.contest;
      if (s) {
        this.contestId = s.id;
        API.list_submissions(this.contestId, 1).then((submissions) => {
          this.submissions = submissions;
          this.requestUpdate();
        });
      }
    });
  }

  goToPage() {
    API.list_submissions(this.contestId!, this.page).then(submissions => {
      this.submissions = submissions;
      this.requestUpdate();
    });
  }

  goToPrev() {
    if (this.page > 1) {
      this.page--;
      this.goToPage();
    }
  }

  goToNext() {
    this.page = this.page + 1;
    this.goToPage();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.subscription) {
      this.subscription.unsubscribe();
      this.subscription = null;
    }
  }

  render() {
    if (!session.contest) {
      return html``;
    }

    const nodes = this.submissions.map(s => {
      const url = router.generate('contest-submission', { id: session.contest!.id, submission_id: s.id });
      return html`
        <tr>
          <td>${format_datetime_detail(s.created)}</td>
          <td>${[s.problem_id]}</td>
          <td>${s.user_id}</td>
          <td>${session.environment_mapping[s.environment_id].name}</td>
          <td>${getSubmittionStatusMark(s.status)}${s.status}</td>
          <td><a is="router_link" href="${url}">詳細</td>
        </tr>`;
    });
    return html`
      <div id="pagenation">
        <button @click="${this.goToPrev}">&lt;</button>
        <span>${this.page}ページ目</span>
        <button @click="${this.goToNext}">&gt;</button>
      </div>
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
