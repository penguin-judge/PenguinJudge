import { Subscription, merge } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { router, session } from '../state';

@customElement('x-contest-tasks')
export class AppContestTasksElement extends LitElement {
  subscription: Subscription | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.subscription = merge(
      session.contest_subject,
      session.current_user,
    ).subscribe(_ => {
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
    const is_admin = (session.current_user.value && session.current_user.value.admin);
    const contest = session.contest!;
    if (!contest)
      return html``;  // 404?
    if (!contest.problems && !is_admin) {
      return html`<div>コンテスト開催前です</div>`;
    }
    const dom_problems: Array<Object> = [];
    if (contest.problems) {
      contest.problems.forEach((problem) => {
        const url = router.generate('contest-task', { id: contest.id, task_id: problem.id });
        dom_problems.push(html`<tr>
                          <td><a is="router-link" href="${url}">${problem.id}</a></td>
                          <td><a is="router-link" href="${url}">${problem.title}</a></td>
                          <td>${problem.time_limit} sec</td>
                          <td>${problem.memory_limit} MiB</td>
                          <td>${problem.score}点</td>
                          </tr>`)
      });
    }
    let admin_links;
    if (is_admin) {
      admin_links = html`
        <span tabindex="0">
          <a is="router-link" href="${router.generate('contest-task-new', {id: contest.id})}" title="問題を追加">
            <x-icon>add</x-icon>
          </a>
        </span>
      `;
    }
    return html`
      <table>
        <thead><tr><th>${admin_links}</th><th>問題名</th><th>実行時間制限</th><th>メモリ制限</th><th>配点</th></tr></thead>
        <tbody>${dom_problems}</tbody>
      </table>
    `
  }

  static get styles() {
    return css`
    table {
      border-collapse: collapse;
    }
    th, td {
      border: solid 1px #ddd;
      padding: 1ex 2ex;
      text-align: left;
      white-space: nowrap;
    }
    tbody tr:nth-child(odd) {
      background-color: #f1f1f1;
    }
    th:nth-child(2), td:nth-child(2) {
      width: 100%;
    }
    td:nth-child(3), td:nth-child(4), td:nth-child(5) {
      text-align: right;
    }
    `
  }
}
