import { customElement, LitElement, html, css } from 'lit-element';
import { Subscription } from 'rxjs';
import { session, default_api_error_handler } from '../state';
import { API } from '../api';

@customElement('x-profile')
export class ProfilePageElement extends LitElement {
  subscription: Subscription | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.subscription = session.current_user.subscribe(_ => {
      this.requestUpdate();
    }, default_api_error_handler);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.subscription)
      this.subscription.unsubscribe();
  }

  _update() {
    const user = session.current_user.value;
    if (!user) return;
    const root = this.shadowRoot!;
    const body: { [key: string]: string; } = {};
    const input_name = <HTMLInputElement>root.getElementById('name');
    const [input_old, input_new] = this._get_password_elements();
    if (user.name !== input_name.value)
      body['name'] = input_name.value;
    if (!this._validate()) {
      const first_invalid_element = root.querySelector(':invalid');
      if (first_invalid_element) {
        (<HTMLInputElement>first_invalid_element).focus();
        (<HTMLInputElement>first_invalid_element).select();
      }
      return;
    }
    if (input_old.value !== '') {
      body['old_password'] = input_old.value;
      body['new_password'] = input_new.value;
    }
    if (Object.getOwnPropertyNames(body).length > 0) {
      API.update_user(user.id, body).then(_ => {
        window.location.reload();
      }, (e) => {
        if (e.status === 409) {
          alert('指定された名前は他のユーザによって既に利用されています');
        } else if (e.status === 401) {
          alert('現在のパスワードが異なります');
        } else {
          alert(e.status + ': ' + e.json);
        }
      });
    }
    return;
  }

  _validate(): boolean {
    const [input_old, input_new, input_confirm] = this._get_password_elements();
    const [pass_old, pass_new, pass_confirm] = [input_old.value, input_new.value, input_confirm.value];
    let ret = true;
    const check_length = (e: HTMLInputElement) => {
      if (e.value.length >= 6 && e.value.length <= 256) {
        return;
      }
      ret = false;
      e.setCustomValidity('invalid length');
    };
    input_old.setCustomValidity('');
    input_new.setCustomValidity('');
    input_confirm.setCustomValidity('');
    if (pass_old === '' && pass_new === '' && pass_confirm === '')
      return ret;
    if (pass_old !== '') {
      check_length(input_old);
      if (pass_new === '') {
        input_new.setCustomValidity('required');
        ret = false;
      } else {
        check_length(input_new);
      }
    }
    if (pass_new !== pass_confirm) {
      input_confirm.setCustomValidity('mismatch');
      ret = false;
    }
    return ret;
  }

  _get_password_elements(): [HTMLInputElement, HTMLInputElement, HTMLInputElement] {
    const root = this.shadowRoot!;
    return [
        <HTMLInputElement>root.getElementById('old_pass'),
        <HTMLInputElement>root.getElementById('new_pass'),
        <HTMLInputElement>root.getElementById('confirm_pass')];
  }

  render() {
    if (session.current_user.value === null)
      return html``;
    const u = session.current_user.value;
    return html`
      <div class="container">
        <h1>Public profile</h1>
        <div class="item">
          <label for="id">ID:</label>
          <input type="text" value="${u.id}" id="id" readonly>
        </div>
        <div class="item">
          <label for="name">Name:</label>
          <input type="text" value="${u.name}" id="name" minlength="3" maxlength="256" required>
        </div>
      </div>
      <div class="container">
        <h1>Account &amp; Security</h1>
        <div class="item">
          <label for="login_id">Login ID:</label>
          <input type="text" value="${u.login_id}" id="login_id" readonly>
        </div>
        <div class="item">
          <label for="old_pass">Old password:</label>
          <input type="password" id="old_pass" @input="${this._validate}">
        </div>
        <div class="item">
          <label for="new_pass">New password:</label>
          <input type="password" id="new_pass" @input="${this._validate}">
        </div>
        <div class="item">
          <label for="confirm_pass">Confirm new password:</label>
          <input type="password" id="confirm_pass" @input="${this._validate}">
        </div>
      </div>
      <div class="container">
        <button @click="${this._update}">更新</button>
      </div>
    `;
  }

  static get styles() {
    return css`
      .container { display: flex; flex-direction: column; align-items: center; }
      .item { display: flex; flex-direction: column; width: 20em; }
      h1 { font-size: large; margin-top: 1em; margin-bottom: 0; }
      label { font-size: 90%; margin-top: 0.5ex; }
      .container:last-of-type { margin-top: 1em; }
      input:invalid { box-shadow: 0 0 5px 1px red; }
      input:focus:invalid { box-shadow: none; }
      input:read-only { background-color: #eee; border: 1px solid #ccc; }
    `;
  }
}
