import { customElement, LitElement, html, css, unsafeCSS } from 'lit-element';
import { BsSpacingCss } from '@lit-element-bootstrap/utilities';
import { HeaderHeightPx } from './consts';
import { router, session } from './state';

@customElement('penguin-judge-header')
export class PenguinJudgeHeaderElement extends LitElement {
  constructor() {
    super();
    session.contest_subject.subscribe(_ => {
      this.requestUpdate();
    });
  }

  render() {
    let title = 'Penguin Judge';
    //let title_link = router.generate('home');
    if (session.contest) {
      title = session.contest.title;
      //title_link = router.generate('contest-top', {id: session.contest.id});
    }
    return html`
    <bs-navbar navbar-light expand-lg class="bg-light" style="background-color: #e3f2fd;">
        <bs-navbar-brand-link><img id="icon" src="/images/penguin.png"></bs-navbar-brand-link>
        <bs-navbar-brand-link>${title}</bs-navbar-brand-link>
        <bs-navbar-nav class="mr-auto">
            <bs-nav-item><bs-nav-link active href="${router.generate('home')}">HOME
            </bs-nav-link></bs-nav-item>
            <bs-nav-item><bs-nav-link href="${router.generate('contests')}">
                コンテスト
            </bs-nav-link></bs-nav-item>
        </bs-navbar-nav>
        <bs-navbar-nav>
          <bs-nav-item>
              <bs-dropdown>
                  <bs-link-button dropdown-nav-link dropdown-toggle><x-icon key="person"></x-icon>ringo</bs-link-button>
                  <bs-dropdown-menu down x-placement="bottom-start">
                      <bs-dropdown-item-link title="個人ページ" @bs-dropdown-item-click="${this.handler}" href="${router.generate('personal')}"></bs-dropdown-item-link>
                      <bs-dropdown-divider></bs-dropdown-divider>
                      <bs-dropdown-item-link title="設定" @bs-dropdown-item-click="${this.handler}" href="${router.generate('setting')}"></bs-dropdown-item-link>
                      <bs-dropdown-item-link title="ログアウト" @bs-dropdown-item-click="${this.handler}" href="${router.generate('logout')}"></bs-dropdown-item-link>
                  </bs-dropdown-menu>
              </bs-dropdown>
          </bs-nav-item>
        </bs-navbar-nav>
    </bs-navbar>
    <br>
    `;
  }

  handler(e: MouseEvent) {
    e.preventDefault();
    router.navigate((<any>e.target).href);
  }

  static get styles() {
    return [
      BsSpacingCss,
      css`
    #icon {
      height: ${unsafeCSS(HeaderHeightPx * 0.6)}px;
    }
    `];
  }
}
