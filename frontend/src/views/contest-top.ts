import { Subscription } from 'rxjs';
import { customElement, LitElement, html } from 'lit-element';
import { session } from '../state';
import { format_datetime_detail } from '../utils';

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
    const contest = session.contest;
    if (!contest) {
      return html``
    }

    // <wc-markdown>の後に改行が必要
    return html`<div>コンテスト期間: ${format_datetime_detail(contest.start_time)} 〜 ${format_datetime_detail(contest.end_time)}</div>
<wc-markdown>
${contest.description}
</wc-markdown>`
  }
}
