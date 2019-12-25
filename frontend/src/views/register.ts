import { customElement, LitElement, html, css } from 'lit-element';
import { MainAreaPaddingPx } from './consts';
import { API } from '../api';
import { router, session } from '../state';

@customElement('x-register')
export class RegisterElement extends LitElement {
  errorMsg: String | null = null;
  isWaitingResponce: boolean = false;

  constructor() {
    super();
    this.updateComplete.then(_ => {
      const e = <HTMLInputElement>this.shadowRoot!.querySelector('#userid');
      if (e) {
        e.focus();
      }
    });
  }

  async post(e: Event) {
    if (!this.shadowRoot) return;
    const userid = (<HTMLInputElement>this.shadowRoot.getElementById("userid")).value;
    const username = (<HTMLInputElement>this.shadowRoot.getElementById("username")).value;
    const password = (<HTMLInputElement>this.shadowRoot.getElementById("password")).value;

    e.preventDefault();
    this.isWaitingResponce = true;
    this.requestUpdate();
    try {
      await API.register(userid, username, password);
      session.update_current_user();
      router.navigate('login');
    } catch (err) {
      if (err.status === 409) this.errorMsg = '既に存在するユーザIDです';
      else if (err.status === 400) this.errorMsg = '使用できない文字列が使われたり、パスワードが短すぎる可能性があります';
      else if (err.status >= 500 && err.status <= 503) this.errorMsg = 'サーバ側のエラーです';
      else this.errorMsg = err.status;
    } finally {
      this.isWaitingResponce = false;
      this.requestUpdate();
    }
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
          <label for="username"></label>
          <input id="username" autofocus placeholder="ユーザ名（表示名）"></input>
        </div>
        <div class="form-item">
          <label for="password"></label>
          <input type="password" id="password" placeholder="パスワード(8文字以上)"></input>
        </div>
        <div class="button-panel">
          <button @click="${this.post}" ?disabled="${this.isWaitingResponce}" class="button">ユーザ登録</button>
        </div>
      </form>
      <div class="form-footer">
        <p><a is="router-link" href="${router.generate('login')}">If you already registered.</a></p>
        ${this.errorMsg !== null ?
        html`
            <p style="color:red;">
              ${this.errorMsg}
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
