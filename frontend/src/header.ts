import { customElement, LitElement, html, css, unsafeCSS } from 'lit-element';
import { HeaderHeightPx } from './consts';
import { router, session } from './state';
import '@lit-element-bootstrap/content'
import '@lit-element-bootstrap/utilities'
import '@lit-element-bootstrap/layout';
import '@lit-element-bootstrap/button';
import '@lit-element-bootstrap/navs';
import '@lit-element-bootstrap/navbar';
import '@lit-element-bootstrap/form';
import '@lit-element-bootstrap/dropdown'

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
            <bs-nav-item><bs-nav-link active>
              <x-anchor href="${router.generate('home')}">Home</x-anchor>
            </bs-nav-link></bs-nav-item>
            <bs-nav-item><bs-nav-link>
              <x-anchor href="${router.generate('contests')}">
                コンテスト
              </x-anchor>
            </bs-nav-link></bs-nav-item>
        </bs-navbar-nav>
        <bs-navbar-nav>
          <bs-nav-item>
              <bs-dropdown>
                  <bs-link-button dropdown-nav-link dropdown-toggle><x-icon key="person"></x-icon>ringo</bs-link-button>
                  <bs-dropdown-menu down x-placement="bottom-start">
                      <bs-dropdown-item-link title="Action" href="${router.generate('contests')}"></bs-dropdown-item-link>
                      <bs-dropdown-item-link title="Another action" index="1"></bs-dropdown-item-link>
                      <bs-dropdown-item-link title="Something else here" index="2"></bs-dropdown-item-link>
                  </bs-dropdown-menu>
              </bs-dropdown>
          </bs-nav-item>
        </bs-navbar-nav>
    </bs-navbar>
    `;
  }

  static get styles() {
    return css`
    #icon {
      height: ${unsafeCSS(HeaderHeightPx * 0.6)}px;
    }
    `;
  }
}
