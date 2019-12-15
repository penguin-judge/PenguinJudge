import { from, Subscription } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { MainAreaPaddingPx } from './consts';
import { API } from '../api';
import { router, session } from '../state';

@customElement('x-register')
export class RegisterElement extends LitElement {
  subscription: Subscription | null = null;
  errorMsg: String | null = null;

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.subscription) {
      this.subscription.unsubscribe();
      this.subscription = null;
    }
  }

  post(e: Event) {
    if (!this.shadowRoot) return;
    const userid = (<HTMLInputElement>this.shadowRoot.getElementById("userid")).value;
    const username = (<HTMLInputElement>this.shadowRoot.getElementById("username")).value;
    const password = (<HTMLInputElement>this.shadowRoot.getElementById("password")).value;

    this.subscription = from(API.register(userid, username, password)).subscribe(
      _ => {
        session.update_current_user();
      },
      err => {
        if (err.status === 409) this.errorMsg = '既に存在するユーザIDです';
        if (err.status >= 500 && err.status <= 503) this.errorMsg = 'サーバ側のエラーです';
        this.requestUpdate();
      },
      () => {
        // redirect
        router.navigate('login');
      }
    );

    e.preventDefault();
  }

  render() {
    return html`
      <x-panel header="ユーザ登録">
        <form>
            ${this.errorMsg !== null ?
        html`
          <div>
            ${this.errorMsg}
          </div>
          <br>` : html``}
          <div>
            <label>ユーザID:&nbsp;<input id="userid" autofocus></label>
            <br>
            <label>ユーザ名:&nbsp;<input id="username"></label>
            <br>
            <label>パスワード:&nbsp;<input id="password" type="password" minlength="8"></label>
            <br>
            <button @click="${this.post}">送信</button>
          </div>
        </form>
      </x-panel>
    `
  }

  static get styles() {
    return css`
      :host {
        display: flex;
        flex-direction: column;
        padding: ${MainAreaPaddingPx}px;
      }
      x-panel {
        margin-bottom: 20px;
      }
    `
  }
}
