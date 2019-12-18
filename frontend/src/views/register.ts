import { customElement, LitElement, html, css } from 'lit-element';
import { MainAreaPaddingPx } from './consts';
import { API } from '../api';
import { router, session } from '../state';

@customElement('x-register')
export class RegisterElement extends LitElement {
  errorMsg: String | null = null;
  isWaitingResponce: boolean = false;

  disconnectedCallback() {
    super.disconnectedCallback();
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
      else if (err.status >= 500 && err.status <= 503) this.errorMsg = 'サーバ側のエラーです';
      else this.errorMsg = err.status;
    } finally {
      this.isWaitingResponce = false;
      this.requestUpdate();
    }
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
            <button @click="${this.post}" ?disabled="${this.isWaitingResponce}">登録</button>
          </div>
          <div>登録済みの場合は<a is="router-link" href="${router.generate('login')}">こちら</a></div>
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
