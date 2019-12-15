import { BehaviorSubject, Subscription, merge, interval } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { API } from '../api';
import { session } from '../state';
import {
  format_datetime_detail,
  input_date_time_elements_to_iso8601,
  split_datetime,
} from '../utils';

@customElement('x-contest-top')
export class AppContestTopElement extends LitElement {
  subscription: Subscription | null = null;
  notify = new BehaviorSubject<any>(null);
  previewSubscription : Subscription | null = null;
  editing = false;

  connectedCallback() {
    super.connectedCallback();
    this.subscription = merge(
      session.current_user,
      session.contest_subject,
      this.notify,
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
    this._unsubscribePreview();
  }

  handlePublish() {
    if (window.confirm('このコンテストを公開してもいいですか？')) {
      API.update_contest(session.contest!.id, {published: true}).then(c => {
        session.update_contest(c);
      });
    }
  }

  handleUnpublish() {
    if (window.confirm('このコンテストを非公開にしてもいいですか？')) {
      API.update_contest(session.contest!.id, {published: false}).then(c => {
        session.update_contest(c);
      });
    }
  }

  handleEdit() {
    this.editing = true;
    this.notify.next(null);
    this.previewSubscription = interval(500).subscribe(_ => {
      if (!this.editing) return;
      const root = this.shadowRoot!;
      (<any>root.querySelector('wc-markdown')).value = (<HTMLTextAreaElement>root.querySelector('textarea')).value;
    });
  }

  _unsubscribePreview() {
    if (this.previewSubscription) {
      this.previewSubscription.unsubscribe();
      this.previewSubscription = null;
    }
  }

  handleUpdate() {
    this._unsubscribePreview();
    this.editing = false;
    const root = this.shadowRoot!;
    const start = input_date_time_elements_to_iso8601(
      <HTMLInputElement>root.querySelector('input[name=start-date]'),
      <HTMLInputElement>root.querySelector('input[name=start-time]'),
    );
    const end = input_date_time_elements_to_iso8601(
      <HTMLInputElement>root.querySelector('input[name=end-date]'),
      <HTMLInputElement>root.querySelector('input[name=end-time]'),
    );
    API.update_contest(session.contest!.id, {
      start_time: start,
      end_time: end,
      description: (<HTMLTextAreaElement>root.querySelector('textarea')).value,
    }).then(c => {
      session.update_contest(c);
    });
  }

  handleCancel() {
    this._unsubscribePreview();
    this.editing = false;
    this.notify.next(null);
  }

  render() {
    const contest = session.contest;
    const user = session.current_user.value;
    if (!contest || !user) {
      return html``
    }

    // <wc-markdown>の後に改行が必要
    const md_preview = html`<wc-markdown>
${contest.description}</wc-markdown>`;
    
    if (this.editing) {
      const start = split_datetime(contest.start_time);
      const end = split_datetime(contest.end_time);
      return html`<div id="edit-container">
        ${md_preview}
        <div id="edit-pane">
          <div>
            <button @click="${this.handleUpdate}">更新</button>
            <button @click="${this.handleCancel}">キャンセル</button>
          </div>
          <div>
            <label for="start-date">開始日時</label>
            <input type="date" name="start-date" value="${start[0]}">
            <input type="time" name="start-time" value="${start[1]}">
          </div>
          <div>
            <label for="end-date">終了日時</label>
            <input type="date" name="end-date" value="${end[0]}">
            <input type="time" name="end-time" value="${end[1]}">
          </div>
          <textarea>${contest.description}</textarea>
        </div>
      </div>`;
    } else {
      let admin_toolbar;
      if (user.admin) {
        const buttons = [html`<a href="javascript:" title="編集" @click="${this.handleEdit}"><x-icon>edit</x-icon></a>`];
        if (contest.published) {
          buttons.push(html`<a href="javascript:" title="非公開にする" @click="${this.handleUnpublish}"><x-icon>block</x-icon></a>`);
        } else {
          buttons.push(html`<a href="javascript:" title="公開する" @click="${this.handlePublish}"><x-icon>publish</x-icon></a>`);
        }
        admin_toolbar = html`<div id="admin-toolbar">${buttons}</div>`;
      }
      return html`${admin_toolbar}
        <div>コンテスト期間: ${format_datetime_detail(contest.start_time)} 〜 ${format_datetime_detail(contest.end_time)}</div>
        ${md_preview}`;
    }
  }

  static get styles() {
    return css`
      #admin-toolbar {
        font-size: x-large;
        float: right;
      }
      #edit-container {
        display: flex;
        height: 100%;
      }
      #edit-container > * {
        flex-grow: 1;
      }
      #edit-pane {
        display: flex;
        flex-direction: column;
      }
      #edit-pane textarea {
        flex-grow: 1;
      }
    `;
  }
}
