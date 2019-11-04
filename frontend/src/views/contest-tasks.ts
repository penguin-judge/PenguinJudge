import { Subscription } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { router, session } from '../state';

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
        const url = router.generate('contest-task', { id: contest_id, task_id: problem.id });
        dom_problems.push(html`<tr>
                          <td><a is="router-link" href="${url}">${problem.id}</a></td>
                          <td><a is="router-link" href="${url}">${problem.title}</a></td></tr>`)
      });
    }
    return html`
      <h1>問題</h1>
      <table>
        <thead><tr><th></th><th>問題名</th></tr></thead>
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
    }
    tbody tr:nth-child(odd) {
      background-color: #f1f1f1;
    }
    `
  }
}
