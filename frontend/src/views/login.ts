import { from, Subscription } from 'rxjs';
import { customElement, LitElement, html, css } from 'lit-element';
import { MainAreaPaddingPx } from './consts';
import { API } from '../api';
import { router, session } from '../state';

@customElement('x-login')
export class AppHomeElement extends LitElement {
  subscription: Subscription | null = null;
  errorStr: String | null = null;

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
    const password = (<HTMLInputElement>this.shadowRoot.getElementById("password")).value;

    this.subscription = from(API.login(userid, password)).subscribe(
      _ => {
        session.update_current_user();
      },
      err => {
        if (err.status === 404 || err.status === 400) this.errorStr = 'ユーザIDまたはパスワードが違います';
        if (err.status >= 500 && err.status <= 503) this.errorStr = 'サーバ側のエラーです';
        this.requestUpdate();
      },
      () => {
        // redirect
        router.navigate('contests');
      }
    );

    e.preventDefault();
  }

  render() {
    return html`
    <div class="form-wrapper">
      <form>
        <div class="form-item">
          <label for="userid"></label>
          <input id="userid" autofocus placeholder="ユーザID"></input>
        </div>
        <div class="form-item">
          <label for="password"></label>
          <input type="password" id="password" placeholder="パスワード"></input>
        </div>
        <div class="button-panel">
          <button @click="${this.post}" class="button">ログイン</button>
        </div>
      </form>
      <div class="form-footer">
        <p><a is="router-link" href="${router.generate('register')}">Create a new account</a></p>
        ${this.errorStr !== null ?
        html`
            <p style="color:red;">
              ${this.errorStr}
            </p>` : html``}
      </div>
    </div>
    `
  }

  static get styles() {
    return css`
      :host {
        padding: ${MainAreaPaddingPx}px;
      }

      * { margin: 0; padding: 0; box-sizing: border-box; }

      .form-wrapper {
        margin: 3em auto;
        padding: 0 1em;
        width: 370px;
        border: 1px solid darkgrey;
        border-radius: 10px;
        font-size: 1em;
      }

      form {
        padding: 0 1.5em;
      }

      .form-item {
        margin-bottom: 0.7em;
      }

      .form-item:first-child {
        margin-top: 2em;
      }

      .form-item input {
        background: inherit;
        border: none;
        border-bottom: 2px solid #eee;
        font-size: 1em;
        height: 2em;
        transition: border-color 0.3s;
        width: 100%;
      }

      .form-item input:focus {
        border-bottom-color: #ccc;
        outline: none;
      }

      .button-panel {
        margin: 1.5em 0 0;
      }

      .button-panel .button {
        background: #6495ed;
        border: none;
        color: #fff;
        cursor: pointer;
        height: 50px;
        font-size: 1.2em;
        letter-spacing: 0.05em;
        text-align: center;
        transition: background 0.3s ease-in-out;
        width: 100%;
      }

      .button:hover {
        background: #4169e1;
      }

      .form-footer {
        padding: 1em 0;
        text-align: center;
      }

      .form-footer a {
        color: #8c8c8c;
        text-decoration: none;
        transition: border-color 0.3s;
      }

      .form-footer a:hover {
        border-bottom: 1px dotted #8c8c8c;
      }
    `
  }
}
