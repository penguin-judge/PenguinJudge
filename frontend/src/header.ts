import { customElement, LitElement, html, css, unsafeCSS } from 'lit-element';
import { HeaderHeight, HeaderHeightPx } from './consts';
//import { router, session } from './state';
import {session} from './state';
import '@lit-element-bootstrap/layout';
import '@lit-element-bootstrap/button';
import '@lit-element-bootstrap/navs';
import '@lit-element-bootstrap/navbar';
import '@lit-element-bootstrap/form';

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
//    let title_link = router.generate('home');
    if (session.contest) {
      title = session.contest.title;
//      title_link = router.generate('contest-top', {id: session.contest.id});
    }
    return html`
    <bs-navbar navbar-light expand-lg class="bg-light">
        <bs-navbar-brand-link><img id="icon" src="/images/penguin.png"> ${title}</bs-navbar-brand-link>
        <bs-navbar-collapse>
            <bs-navbar-nav>
                <bs-nav-item><bs-nav-link active>Home</bs-nav-link></bs-nav-item>
                <bs-nav-item><bs-nav-link>Features</bs-nav-link></bs-nav-item>
                <bs-nav-item><bs-nav-link>Pricing</bs-nav-link></bs-nav-item>
                <bs-nav-item><bs-nav-link disabled>Disabled</bs-nav-link></bs-nav-item>
            </bs-navbar-nav>
        </bs-navbar-collapse>
    </bs-navbar>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: flex;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: ${HeaderHeight};
        background-color: #eee;
        align-items: center;
      }
      #icon-area {
        height: ${HeaderHeight};
        width: ${HeaderHeight};
        display: flex;
        align-items: center;
        justify-content: center;
      }
      #icon {
        height: ${unsafeCSS(HeaderHeightPx * 0.7)}px;
      }
      #title {
        font-weight: bold;
        font-size: 130%;
      }
      #title x-anchor {
        color: black;
        text-decoration: none;
      }
      #extra {
        flex-grow: 1;
        text-align: right;
        margin-right: 1em;
      }
      x-icon {
        font-size: 22px;
        width: 22px;
        vertical-align: top;
      }
      .dropdown-caret {
        display: inline-block;
        width: 0;
        height: 0;
        vertical-align: middle;
        border-top-style: solid;
        border-top-width: 4px;
        border-right: 4px solid transparent;
        border-bottom: 0px solid transparent;
        border-left: 4px solid transparent;
      }
    `;
  }
}
