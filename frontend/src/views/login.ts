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
    console.log(userid, password);

    this.subscription = from(API.login(userid, password)).subscribe(
      json => {
        // save token
        session.token = json.token;
      },
      err => {
        this.errorStr = err;
        console.log(2, err, this.errorStr);
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
      <x-panel header="ログイン">
        ${this.errorStr !== null ?
        html`
            <div>
              ${this.errorStr}
            </div>` : html``}
        <div>
          <form>
            <input id="userid" autofocus>
            <input id="password" type="password" minlength="8">
            <button @click="${this.post}">ログイン</button>
          </form>
        </div>
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
