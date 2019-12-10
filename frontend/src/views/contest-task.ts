import { Subscription } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { API } from '../api';
import { router, session } from '../state';

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
      environment_id: parseInt(env),
    }).then(s => {
      router.navigate(router.generate('contest-submission', {
        id: session.contest!.id,
        submission_id: s.id,
      }));
    }, e => {
      if (e.status === 401) {
        alert("ログインが必要です");
        router.navigate('login');
      }
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

    // <wc-markdown>の後に改行が必要
    return html`
      <div id="problem">
        <div id="title">${task.title}</div>
        <wc-markdown>
${task.description}
</wc-markdown>
      </div>
      <div id="submission">
        <div>
          <select id="env">${dom_langs}</select>
        </div>
        <div>
          <textarea id="code"></textarea>
        </div>
        <div>
          <button @click="${this.post}">提出</button>
        </div>
      </div>
    `
  }

  static get styles() {
    return css`
    :host {
      display: flex;
    }
    #title {
      font-size: 120%;
      font-weight: bold;
      border-bottom: 1px solid #ddd;
      margin-right: 1em;
      margin-bottom: 1em;
    }
    #problem {
      flex-grow: 1;
    }
    #submission {
      display: flex;
      flex-direction: column;
      flex-grow: 1;
    }
    #submission > div:last-child {
      margin-top: 1ex;
      text-align: right;
    }
    #submission > div:nth-child(2) {
      flex-grow: 1;
    }
    textarea {
      width: 100%;
      height: 100%;
    }
    `
  }
}
