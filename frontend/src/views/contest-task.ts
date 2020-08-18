import { Subscription, merge } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { API } from '../api';
import { router, session } from '../state';
import { AceEditor } from '../components/ace';

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
    this.updateComplete.then(() => {
      this.langChanged();
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
    const code = (<AceEditor>this.shadowRoot.getElementById("code")).value;
    if (localStorage)
      localStorage.setItem('lang.id', env);
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

  langChanged() {
    const env = <HTMLSelectElement>this.shadowRoot!.getElementById("env");
    const code = <AceEditor>this.shadowRoot!.getElementById("code");
    if (!env || !code || env.selectedOptions.length == 0) return;
    code.setModeFromAmbiguous(env.selectedOptions[0].textContent!);
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

    const selected_lang_id = localStorage && localStorage.getItem('lang.id');
    const dom_langs = session.environments.map((e) => {
      return html`<option value="${e.id}" ?selected=${e.id!.toString() === selected_lang_id}>${e.name}</option>`;
    });

    return html`
      <div id="problem">
        <div id="title">${task.title}${admin_links}</div>
        <div id="limitation">実行時間制限: ${task.time_limit}秒／メモリ制限: ${task.memory_limit}MiB／配点: ${task.score}点</div>
        <x-markdown class="${new Date() < new Date(session.contest.end_time) ? 'ongoing' : ''}" .value="${task.description}" />
      </div>
      <div id="submission">
        <div id="submission-header">
          <select id="env" @click="${this.langChanged}">${dom_langs}</select>
          <button @click="${this.post}">提出</button>
        </div>
        <div id="submission-codearea">
          <x-ace-editor id="code" autofocus></x-ace-editor>
        </div>
      </div>
    `
  }

  static get styles() {
    return css`
    :host {
      display: grid;
      grid-template-columns: 1fr 1fr;
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
      padding-right: 0.5em;
      margin-right: 0.5em;
      overflow: auto;
    }
    #submission {
      display: flex;
      flex-direction: column;
    }
    #submission-header {
      display: flex;
      justify-content: space-between;
    }
    #submission-header * {
      white-space: nowrap;
    }
    #submission-codearea {
      flex-grow: 1;
      display: flex;
      padding-top: 1ex;
    }
    #code {
      flex-grow: 1;
    }
    #admin-links {}
    #admin-links a {
      font-size: 24px;
      padding: 5px 5px 0 5px;
    }
    #admin-links a:hover {
      background-color: #ddd;
    }
    x-markdown.ongoing {
      margin-bottom: 5em;
    }
    `
  }
}
