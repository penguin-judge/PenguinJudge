//import { Subscription } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { API } from '../api';
import { router } from '../state';
import { input_date_time_elements_to_iso8601 } from '../utils';

@customElement('x-contest-new')
export class AppContestNewElement extends LitElement {
  handleCreate() {
    const root = this.shadowRoot!;
    const names = ['id', 'title'];
    const values = names.map(name => {
      return (<HTMLInputElement>root.querySelector('input[name=' + name + ']')).value;
    });
    const empty_idx = values.findIndex(v => v === '');
    if (empty_idx >= 0) {
      alert(names[empty_idx] + 'を入力してください');
      return;
    }
    const start_time = input_date_time_elements_to_iso8601(
      <HTMLInputElement>root.querySelector('input[name=start-date]'),
      <HTMLInputElement>root.querySelector('input[name=start-time]'),
    );
    const end_time = input_date_time_elements_to_iso8601(
      <HTMLInputElement>root.querySelector('input[name=end-date]'),
      <HTMLInputElement>root.querySelector('input[name=end-time]'),
    );
    if (!start_time || !end_time) {
      alert('開始日時または終了日時を入力してください');
      return;
    }
    const body = {
      'id': values[0],
      'title': values[1],
      'start_time': start_time,
      'end_time': end_time,
      'published': false,
      'description': '# ' + values[1] + '\n\n' + 'ここにコンテストの説明を書いてね',
    };
    API.create_contest(body).then(contest => {
      router.navigate(router.generate('contest-top', {id: contest.id}));
    }, e => {
      alert('エラー. ' + e);
      console.log(e);
    });
  }

  render() {
    return html`
      <h1>コンテストの新規登録</h1>
      <div>
        <label for="id">ID: </label>
        <input type="text" name="id">
      </div>
      <div>
        <label for="title">コンテスト名: </label>
        <input type="text" name="title">
      </div>
      <div>
        <label for="start-date">開始日時: </label>
        <input type="date" name="start-date">
        <input type="time" name="start-time">
      </div>
      <div>
        <label for="end-date">終了日時: </label>
        <input type="date" name="end-date">
        <input type="time" name="end-time">
      </div>
      <button @click="${this.handleCreate}">作成</button>
    `
  }

  static get styles() {
    return css`
    :host {
      margin-left: 1em;
    }
    h1 { font-size: large; }
    `;
  }
}
