import { Subscription, merge } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { API } from '../api';
import { router, session } from '../state';

@customElement('x-contest-task')
export class AppContestTaskElement extends LitElement {
  subscription: Subscription | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.subscription = merge(
      session.environment_subject,
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

  rejudge(e: any) {
    e.preventDefault();
    if (confirm('リジャッジを実行しますか？')) {
      API.rejudge(session.contest!.id, session.task_id!).then(_ => {
        router.navigate(router.generate('contest-submissions', {id: session.contest!.id}));
      }, e => {
        alert('error');
        console.error(e);
      });
    }
  }

  render() {
    if (!session.contest || !session.contest.problems || !session.task_id)
      return html`?`;

    let task = session.contest.problems.find((p) => {
      return p.id === session.task_id;
    });
    if (!task)
      return html`??`;

    let admin_links;
    if (session.current_user.value && session.current_user.value.admin) {
      admin_links = html`<span id="admin-links">
        <span tabindex="0">
          <a is="router-link" href="${router.generate('contest-task-edit', {id: session.contest.id, task_id: task.id})}" title="問題を編集"><x-icon>edit</x-icon></a>
        </span>
        <span tabindex="0">
          <a href="#rejudge" title="リジャッジ" @click="${this.rejudge}"><x-icon>gavel</x-icon></a>
        </span>
      </span>`;
    }

    const dom_langs = session.environments.map((e) => {
      return html`<option value="${e.id}">${e.name}</option>`;
    });

    // <wc-markdown>の後に改行が必要
    return html`
      <div id="problem">
        <div id="title">${task.title}${admin_links}</div>
        <div id="limitation">実行時間制限: ${task.time_limit}秒／メモリ制限: ${task.memory_limit}MiB</div>
        <wc-markdown>
${task.description}
</wc-markdown>
      </div>
      <div id="submission">
        <div id="submission-header">
          <select id="env">${dom_langs}</select>
          <button @click="${this.post}">提出</button>
        </div>
        <div id="submission-codearea">
          <textarea id="code"></textarea>
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
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }
    #limitation {
      font-size: small;
      text-align: right;
    }
    #problem {
      flex-grow: 1;
      margin-right: 1em;
    }
    #submission {
      display: flex;
      flex-direction: column;
      flex-grow: 1;
    }
    #submission-header {
      display: flex;
      justify-content: space-between;
    }
    #submission-codearea {
      flex-grow: 1;
    }
    textarea {
      width: 100%;
      height: 100%;
    }
    #admin-links {}
    #admin-links a {
      font-size: 24px;
      padding: 5px 5px 0 5px;
    }
    #admin-links a:hover {
      background-color: #ddd;
    }
    `
  }
}
