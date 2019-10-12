import { Subscription } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { API } from './api';
import { session } from './state';

@customElement('x-contest-task')
export class AppContestTaskElement extends LitElement {
  subscriptions: Array<Subscription> = [];

  connectedCallback() {
    super.connectedCallback();
    this.subscriptions.push(session.environment_subject.subscribe(_ => this.requestUpdate()));
    this.subscriptions.push(session.contest_subject.subscribe(_ => this.requestUpdate()));
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.subscriptions.forEach((s) => s.unsubscribe());
    this.subscriptions.splice(0);
  }

  post() {
    if (!this.shadowRoot || !session.contest || !session.task_id) return;
    const env = (<HTMLSelectElement>this.shadowRoot.getElementById("env")).value;
    const code = (<HTMLTextAreaElement>this.shadowRoot.getElementById("code")).value;
    API.submit({
      contest_id: session.contest.id,
      problem_id: session.task_id,
      code: code,
      environment_id: env,
    });
  }

  render() {
    if (!session.contest || !session.contest.problems || !session.task_id)
      return html`?`;

    let task = session.contest.problems.find((p) => {
      return p.id === session.task_id;
    });
    if (!task)
      return html`??`;

    const dom_langs = session.environments.map((e) => {
      return html`<option value="${e.id}">${e.name}</option>`;
    });

    return html`
      <h1>${task.title}</h1>
      <h2>問題文</h2>
      <p>${task.description}</p>
      <h2>提出</h2>
      <form>
        <div>
          <div class="c1">言語:</div>
          <div class="c2"><select id="env">${dom_langs}</select></div>
        </div>
        <div>
          <div class="c1">ソースコード:</div>
          <textarea id="code" class="c2"></textarea>
        </div>
        <div>
          <div class="c1"></div>
          <div class="c2">
            <button @click="${this.post}">提出</button>
          </div>
        </div>
      </form>
    `
  }

  static get styles() {
    return css`
    form {
      display: flex;
      flex-direction: column;
      padding-right: 1em;
    }
    form > div {
      display: flex;
    }
    form > div:first-child {
      align-items: center;
    }
    form > div:nth-child(2) > div:first-child {
      padding-top: 0.5ex;
    }
    .c1 {
      width: 7em;
      text-align: right;
      padding-right: 1ex;
    }
    .c2 {
      flex-grow: 1;
    }
    textarea {
      height: 20em;
    }
    `
  }
}
