import { customElement, LitElement, html, css } from 'lit-element';
import { API } from '../api';
import { router, session } from '../state';

@customElement('x-contest-task-new')
export class AppContestTaskNewElement extends LitElement {
  handleCreate() {
    const root = this.shadowRoot!;
    const contest = session.contest!;
    const id = (<HTMLInputElement>root.querySelector('input[name=id]')).value;
    const title = (<HTMLInputElement>root.querySelector('input[name=title]')).value;
    if (!id || !title) {
      alert('IDまたはタイトルを入力してください');
      return;
    }
    API.create_problem(contest.id, {
      id: id, title: title, description: '',
      time_limit: 10, memory_limit: 512, score: 100,
    }).then(problem => {
      router.navigate(router.generate('contest-task-edit', {
        id: contest.id,
        task_id: problem.id,
      }));
    }, (e: any) => {
      alert('error');
      console.error(e);
    });
  }

  render() {
    return html`
      <h1>問題の新規登録</h1>
      <div>
        <label for="id">ID: </label>
        <input type="text" name="id">
      </div>
      <div>
        <label for="title">問題名: </label>
        <input type="text" name="title">
      </div>
      <button @click="${this.handleCreate}">作成</button>
    `
    return html`Hello`;
  }

  static get styles() {
    return css`
    :host {
      margin-left: 1em;
    }
    h1 { font-size: large; }
    `
  }
}
