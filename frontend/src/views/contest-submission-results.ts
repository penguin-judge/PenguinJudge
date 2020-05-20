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
  order_key = '';

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
    const query = new Map<string, string>();
    query.set('page', this.page_index.toString());
    {
      [['problem-filter', 'problem_id'],
       ['env-filter', 'environment_id'],
       ['status-filter', 'status'],
       ['user-filter', 'user_name']].forEach(([k0, k1]) => {
         const element = <HTMLInputElement>this.shadowRoot!.getElementById(k0);
         if (!element || element.value === '') return;
         query.set(k1, element.value);
       });
    }
    if (this.order_key) {
      query.set('sort', this.order_key);
    }
    API.list_submissions(session.contest!.id, query).then(([submissions, resp]) => {
      const x_total_pages = resp.headers.get('x-total-pages');
      if (x_total_pages)
        this.number_of_pages = parseInt(x_total_pages);
      this.submissions = submissions;
      this.requestUpdate();
    }, _ => {});
  }

  _sort(key: string) {
    if (this.order_key === key) {
      this.order_key = '-' + key;
    } else {
      this.order_key = key;
    }
    this.page_index = 1;
    this.loadSubmissions();
  }

  render() {
    if (!session.contest) {
      return html``;
    }
    if (!session.contest.problems) {
      return html`<div>コンテスト開催前です</div>`;
    }

    const pagenation = html`<penguin-judge-pagenation pages="${this.number_of_pages}" currentPage="${this.page_index}" @page-changed="${this.changePage}"></penguin-judge-pagenation>`;

    const nodes = this.submissions.map(s => {
      const url = router.generate('contest-submission', { id: session.contest!.id, submission_id: s.id });
      return html`
        <tr>
          <td>${format_datetime_detail(s.created)}</td>
          <td><a is="router_link" href="${router.generate('contest-task', { id: session.contest!.id, task_id: [s.problem_id] })}">${[s.problem_id]}</a></td>
          <td>${s.user_name}</td>
          <td>${session.environment_mapping[s.environment_id].name}</td>
          <td>${getSubmittionStatusMark(s.status)}${s.status}</td>
          <td>${s.code_bytes} B</td>
          <td>${Math.floor(s.max_time * 1000)} ms</td>
          <td>${Math.floor(s.max_memory)} KiB</td>
          <td><a is="router_link" href="${url}">詳細</td>
        </tr>`;
    });
    return html`
      ${pagenation}
      <table id="submission_list">
        <thead><tr><td colspan="9" id="filter-column"><div>
            <label for="problem-filter">問題:</label>
            <select id="problem-filter" @input="${this.loadSubmissions}">
              <option value="" selected>-</option>
              ${session.contest.problems.map(p => {
                return html`<option value="${p.id}">${p.id}: ${p.title}</option>`;
              })}
            </select>
            <label for="env-filter">言語:</label>
            <select id="env-filter" @input="${this.loadSubmissions}">
              <option value="" selected>-</option>
              ${session.environments.map(e => {
                return html`<option value="${e.id}">${e.name}</option>`;
              })}
            </select>
            <label for="status-filter">結果:</label>
            <select id="status-filter" @input="${this.loadSubmissions}">
              <option value="" selected>-</option>
              <option value="Accepted">AC</option>
              <option value="WrongAnswer">WA</option>
              <option value="TimeLimitExceeded">TLE</option>
              <option value="MemoryLimitExceeded">MLE</option>
              <option value="RuntimeError">RE</option>
              <option value="CompilationError">CE</option>
              <option value="OutputLimitExceeded">OLE</option>
              <option value="Waiting">WJ</option>
              <option value="Running">Judging</option>
            </select>
            <label for="user-filter">ユーザ:</label>
            <input id="user-filter" type="text">
            <button @click="${this.loadSubmissions}">フィルタ</button>
          </div></td></tr><tr>
          <td><a @click="${() => this._sort('created')}">提出日時</a></td>
          <td>問題</td>
          <td>ユーザ</td>
          <td>言語</td>
          <td>結果</td>
          <td><a @click="${() => this._sort('code_bytes')}">コード長</a></td>
          <td><a @click="${() => this._sort('max_time')}">実行時間</a></td>
          <td><a @click="${() => this._sort('max_memory')}">メモリ</a></td>
          <td></td></tr>
        </thead>
        <tbody>${nodes}</tbody>
      </table>`;
  }

  static get styles() {
    return css`
    #submission_list {
      border-collapse:collapse;
      margin: auto;
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
    td a {
      color: #0066cb;
    }
    td a:hover {
      cursor: pointer;
      text-decoration: underline;
    }
    tbody tr td:nth-child(n+6) {
      text-align: right;
    }
    #filter-column * {
      font-size: 85%;
    }
    #filter-column label {
      margin-left: 1em;
      margin-right: 2px;
    }
    #filter-column > div {
      display: flex;
      flex-direction: row;
      align-items: center;
    }
    #filter-column input {
      flex-grow: 1;
      margin-right: 1em;
    }
    #filter-column button {
      margin-right: 1em;
      padding: 0;
    }
    `;
  }
}
