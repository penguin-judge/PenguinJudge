import { Subscription } from 'rxjs';
import { customElement, LitElement, html } from 'lit-element';
import { session } from '../state';

@customElement('x-contest-top')
export class AppContestTopElement extends LitElement {
  subscription: Subscription | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.subscription = session.contest_subject.subscribe(_ => {
      this.requestUpdate();
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.subscription) {
      this.subscription.unsubscribe();
      this.subscription = null;
    }
  }

  render() {
    if (!session.contest) {
      return html``
    }
    // <wc-markdown>の後に改行が必要
    return html`<wc-markdown>
${session.contest.description}
</wc-markdown>`
  }
}
