import { Subscription, interval } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { API, Problem } from '../api';
import { router, session } from '../state';

@customElement('x-contest-task-edit')
export class AppContestTaskEditElement extends LitElement {
  previewSubscription : Subscription | null = null;
  problem: Problem | null = null;

  constructor() {
    super();
    if (!session.contest || !session.task_id)
      return;
    API.get_problem(session.contest.id, session.task_id).then(info => {
      this.problem = info;
      this.requestUpdate();
      this.previewSubscription = interval(500).subscribe(_ => {
        const root = this.shadowRoot!;
        (<HTMLDivElement>root.querySelector('#title'))!.textContent = (<HTMLInputElement>root.querySelector('input[name=title]')).value;
        (<any>root.querySelector('wc-markdown')).value = (<HTMLTextAreaElement>root.querySelector('textarea')).value;
      });
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._unsubscribePreview();
  }

  _unsubscribePreview() {
    if (this.previewSubscription) {
      this.previewSubscription.unsubscribe();
      this.previewSubscription = null;
    }
  }

  handleUpdate() {
    const root = this.shadowRoot!;
    const body = {
      title: (<HTMLInputElement>root.querySelector('input[name=title]')).value,
      time_limit: parseInt((<HTMLInputElement>root.querySelector('input[name=time-limit]')).value),
      memory_limit: parseInt((<HTMLInputElement>root.querySelector('input[name=memory-limit]')).value),
      score: parseInt((<HTMLInputElement>root.querySelector('input[name=score]')).value),
      description: (<HTMLTextAreaElement>root.querySelector('textarea')).value,
    };
    if (isNaN(body.time_limit) || isNaN(body.memory_limit) || isNaN(body.score)) {
      alert('時間制限とメモリ制限には数値を入力してください');
      return;
    }
    API.update_problem(session.contest!.id, session.task_id!, body).then(p => {
      const contest = session.contest!;
      if (contest.problems) {
        const i = contest.problems.findIndex(x => x.id === p.id);
        if (i >= 0) {
          contest.problems[i] = p;
        } else {
          contest.problems.push(p);
        }
      } else {
        contest.problems = [p];
      }
      router.navigate(router.generate('contest-task', {
        id: session.contest!.id,
        task_id: session.task_id!,
      }));
    }, e => {
      alert('error');
      console.error(e);
    });
  }

  handleCancel() {
    router.navigate(router.generate('contest-task', {
      id: session.contest!.id,
      task_id: this.problem!.id
    }));
  }

  render() {
    if (!this.problem) {
      return html``;
    }

    // <wc-markdown>の後に改行が必要
    const md_preview = html`<div id="preview-pane">
      <div id="title">${this.problem.title}</div><wc-markdown>
${this.problem.description}</wc-markdown></div>`;

    return html`<div id="edit-container">
      ${md_preview}
      <div id="edit-pane">
        <div>
          <button @click="${this.handleUpdate}">更新</button>
          <button @click="${this.handleCancel}">キャンセル</button>
        </div>
        <div>
          <label for="title">タイトル:</label>
          <input type="text" name="title" value="${this.problem.title}">
        </div>
        <div>
          <label for="score">スコア:</label>
          <input type="number" name="score" value="${this.problem.score}">
        </div>
        <div>
          <label for="time-limit">時間制限[秒]:</label>
          <input type="number" name="time-limit" value="${this.problem.time_limit}">
        </div>
        <div>
          <label for="memory-limit">メモリ上限[MiB]:</label>
          <input type="number" name="memory-limit" value="${this.problem.memory_limit}">
        </div>
        <textarea>${this.problem.description}</textarea>
      </div>
      </div>`;
  }

  static get styles() {
    return css`
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
      #title {
        font-size: 120%;
        font-weight: bold;
        border-bottom: 1px solid #ddd;
        margin-right: 1em;
        margin-bottom: 1em;
      }
    `;
  }
}
