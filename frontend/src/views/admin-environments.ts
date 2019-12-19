import { Subscription } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { API } from '../api';
import { session } from '../state';

@customElement('x-admin-environments')
export class AppEnvironmentsElement extends LitElement {
  subscription : Subscription | null = null;
  editing: number | null = null;

  constructor() {
    super();
    this.subscription = session.environment_subject.subscribe(_ => {
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

  handleRegister() {
    const root = this.shadowRoot;
    if (!root) return;
    const body = {
      name: (<HTMLInputElement>root.getElementById('name')).value,
      compile_image_name: (<HTMLInputElement>root.getElementById('compile_image_name')).value,
      test_image_name: (<HTMLInputElement>root.getElementById('test_image_name')).value,
      active: (<HTMLInputElement>root.getElementById('active')).checked,
    };
    API.register_environment(body).then(_ => {
      session.update_environments();
    }, e => {
      alert('error');
      console.error(e);
    });
  }

  editButtonHandler(env_id: number) {
    return () => {
      this.editing = env_id;
      this.requestUpdate();
    };
  }

  deleteButtonHandler(env_id: number) {
    return () => {
      const e = session.environment_mapping[env_id];
      if (confirm('"' + e.name + '"を削除しても良いですか？')) {
        API.delete_environment(env_id).catch(() => {}).finally(() => {
          session.update_environments();
        });
      }
    };
  }

  handleUpdate() {
    const root = this.shadowRoot;
    if (typeof this.editing !== 'number') return;
    const e = session.environment_mapping[this.editing];
    if (!root || !e) return;
    const body = {
      name: (<HTMLInputElement>root.getElementById('name')).value,
      compile_image_name: (<HTMLInputElement>root.getElementById('compile_image_name')).value,
      test_image_name: (<HTMLInputElement>root.getElementById('test_image_name')).value,
      published: (<HTMLInputElement>root.getElementById('published')).checked,
      active: (<HTMLInputElement>root.getElementById('active')).checked,
    };
    if (body.name === e.name) delete body.name;
    if (body.compile_image_name === e.compile_image_name) delete body.compile_image_name;
    if (body.test_image_name === e.test_image_name) delete body.test_image_name;
    if (body.published === e.published) delete body.published;
    if (body.active === e.active) delete body.active;
    if (Object.keys(body).length === 0) {
      alert('差分がないので更新をスキップします');
      this.handleCancel();
      return;
    }
    API.update_environment(this.editing, body).then(_ => {
      session.update_environments();
    }, e => {
      alert('error');
      console.error(e);
    });
    this.editing = null;
  }

  handleCancel() {
    this.editing = null;
    this.requestUpdate();
  }

  render() {
    const envs = session.environments;
    if (!envs)
      return html``;

    let right_pane;
    if (typeof this.editing === 'number') {
      const e = session.environment_mapping[this.editing];
      right_pane = html`<h2>更新</h2>
      <div id="right-pane">
        <label>ID:</label><input type="text" value="${e.id}" readonly>
        <label for="name">名前:</label><input type="text" id="name" value="${e.name}">
        <label for="compile_image_name">コンパイル用イメージ名:</label><input type="text" id="compile_image_name" value="${e.compile_image_name}">
        <label for="test_image_name">実行用イメージ名:</label><input type="text" id="test_image_name" value="${e.test_image_name}">
        <label for="published">ユーザに公開</label><div><input type="checkbox" id="published" .checked="${e.published}"></div>
        <label for="active">ユーザが新規に利用可能</label><div><input type="checkbox" id="active" .checked="${e.active}"></div>
        <div></div><div style="text-align:right">
          <button @click="${this.handleUpdate}">更新</button>
        <button @click="${this.handleCancel}">キャンセル</button>
        </div>
      </div>`;
    } else {
      right_pane = html`<h2>環境の新規登録</h2>
      <div id="right-pane">
        <label for="name">名前:</label><input type="text" id="name">
        <label for="compile_image_name">コンパイル用イメージ名:</label><input type="text" id="compile_image_name">
        <label for="test_image_name">実行用イメージ名:</label><input type="text" id="test_image_name">
        <label for="published">ユーザに公開</label><div><input type="checkbox" id="published"></div>
        <label for="active">ユーザが新規に利用可能</label><div><input type="checkbox" id="active"></div>
        <div></div><div style="text-align:right"><button @click="${this.handleRegister}">新規登録</button></div>
      </div>`;
    }

    const done = html`<x-icon>done</x-icon>`;
    const rows = envs.map(e => html`<tr><td><button @click="${this.editButtonHandler(e.id!)}"><x-icon>edit</x-icon></button><button @click="${this.deleteButtonHandler(e.id!)}"><x-icon>delete</x-icon></button></td><td>${e.id}</td><td>${e.published ? done : undefined}</td><td>${e.active ? done : undefined}</td><td>${e.name}</td><td>${e.compile_image_name}</td><td>${e.test_image_name}</td></tr>`);
    return html`<h1>実行環境の設定</h1>
      <div id="container">
        <table>
          <thead><tr><th></th><th>#</th><th>公開</th><th>利用可</th><th>名前</th><th>コンパイル用イメージ名</th><th>実行用イメージ名</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <div>${right_pane}</div>
      </div>
    `;
  }

  static get styles() {
    return css`
    :host { margin-left: 1em; }
    h1 { font-size: large; }
    h2 { font-size: medium; margin-top: 0; }
    #container {
      display: flex;
      align-items: flex-start;
      flex-wrap: wrap;
    }
    table {
      margin-right: 1em;
      margin-bottom: 1em;
      border-collapse: collapse;
    }
    th, td {
      border: solid 1px #ddd;
      padding: 0.5ex 1ex;
      text-align: left;
      white-space: nowrap;
    }
    tr td:nth-child(3) {
      text-align: center;
    }
    table button {
      display: inline-block;
      border: 0;
      margin: 0;
      padding: 0;
      cursor: pointer;
    }
    table button:first-child {
      margin-right: 0.5ex;
    }
    table button:hover {
      color: blue;
    }
    #right-pane {
      display: grid;
      grid-template-columns: auto 1fr;
    }
    `;
  }
}
