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

    const langs = session.environments.map((e) => {
      return {"id": e.id, "value": e.name};
    });

    return html`
      <bs-container>
        <div class="header text-dark" style="margin:10px;"><h3>${task.title}</h3></div>
        <div class="body">
        <bs-row>
          <bs-column sm-4 demo>
            ${task.description}
          </bs-column>
          <bs-column sm-7 demo>
            <bs-form>
            <bs-form-group>
              <bs-form-label slot="label">言語</bs-form-label>
              <bs-form-select slot="control"
                        .jsonData=${langs}
                        json-id="id"
                        json-text="value"></bs-form-select>
            </bs-form-group>
            <bs-form-group>
              <bs-form-label slot="label">コード</bs-form-label>
              <bs-form-textarea rows="10" slot="control"></bs-form-textarea>
            </bs-form-group>
            <bs-button primary button-type="submit" action="submit">提出</bs-button>
            </bs-form>
          </bs-column>
        </bs-row>
        </div>
      </bs-container>
    `
  }

  static get styles() {
    return css`
    :host {
      width: 100%;
      height: 100%;
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
