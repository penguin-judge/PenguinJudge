import './header';
import './home';
import './contests';
import './contest-frame';
import './contest-top';
import './contest-tasks';
import './contest-task';
import './contest-submission-results';
import './components/anchor';
import './components/icon';
import './components/panel';
//import { HeaderHeight } from './consts';
import { router, session } from './state';
import { customElement, LitElement, html, css, property } from 'lit-element';
import '@lit-element-bootstrap/content';
import '@lit-element-bootstrap/utilities';
import '@lit-element-bootstrap/layout';
import '@lit-element-bootstrap/badge';
import '@lit-element-bootstrap/breadcrumb';
import '@lit-element-bootstrap/button';
import '@lit-element-bootstrap/button-group';
import '@lit-element-bootstrap/card';
import '@lit-element-bootstrap/carousel';
import '@lit-element-bootstrap/dropdown';
import '@lit-element-bootstrap/form';
import '@lit-element-bootstrap/input-group';
import '@lit-element-bootstrap/jumbotron';
import '@lit-element-bootstrap/list-group';
import '@lit-element-bootstrap/media-object';
import '@lit-element-bootstrap/modal';
import '@lit-element-bootstrap/navbar';
import '@lit-element-bootstrap/alert';
import '@lit-element-bootstrap/pagination';
import '@lit-element-bootstrap/progress';
import '@lit-element-bootstrap/collapse';
import '@lit-element-bootstrap/theme';
import '@lit-element-bootstrap/navs';

import { BsContentRebootCss, BsContentTypographyCss } from '@lit-element-bootstrap/content';
import { BsTextCss, BsTextColorCss, BsSpacingCss, BsDisplayCss } from '@lit-element-bootstrap/utilities';
import { BsFlexDisplayCss,
    BsFlexJustifyCss,
    BsFlexWrapCss,
    BsFlexAlignContentCss,
    BsFlexDirectionCss,
    BsFlexOrderCss } from '@lit-element-bootstrap/utilities';

@customElement('x-root')
export class AppRootElement extends LitElement {
  @property({type: Object}) route = html``;

  constructor() {
    super();
    session.init();

    const routes: Array<[string, string, any, any]> = [
      ['contests', 'contests', html`<x-contests></x-contests>`, null],
      ['contests/:id', 'contest-top', html`<x-contest-top></x-contest-top>`, this._wait_fetch_contest_info],
      ['contests/:id/tasks', 'contest-tasks', html`<x-contest-tasks></x-contest-tasks>`, this._wait_fetch_contest_info],
      ['contests/:id/tasks/:task_id', 'contest-task', html`<x-contest-task></x-contest-task>`, this._wait_fetch_contest_info],
      ['contests/:id/submissions/me', 'contest-submissions-me', html`<penguin-judge-contest-submission-results />`, this._wait_fetch_contest_info],
      ['', 'home', html`<x-home></x-home>`, null],
    ];
    routes.forEach((v) => {
      const [path, name, body, before_hook] = v;
      let hooks: any = undefined;
      if (before_hook) {
        hooks = {before: before_hook};
      }
      router.on(path, {as: name, uses: (params: {[key: string]: string}) => {
        this._route_handler(path, body, params);
      }}, hooks);
    });
    router.notFound((_: any) => {
      this.route = html`<h1>HTTP 404: NOT FOUND</h1>`
    });
    router.resolve();
  }

  private _route_handler(path: string, body: any, params: {[key: string]: string}) {
    if (path.startsWith('contests/')) {
      body = html`<penguin-judge-contest-frame>${body}</penguin-judge-contest-frame>`;
    } else {
      session.leave_contest();
    }
    session.task_id = params && params.hasOwnProperty('task_id') ? params['task_id'] : null;
    this.route = body;
    session.navigated(path);
  }

  private _wait_fetch_contest_info(done: any, params: {[key: string]: string}) {
    session.enter_contest(params.id).then(_ => done());
  }

  render() {
    return html`
    <bs-container>
        <div class="header"><penguin-judge-header></penguin-judge-header></div>
        <div class="body" id="container">${this.route}</div>
    </bs-container>
    `
  }

  static get styles() {
        return [
            BsContentRebootCss,
            BsContentTypographyCss,
            BsTextCss,
            BsTextColorCss,
            BsDisplayCss,
            BsFlexWrapCss,
            BsFlexOrderCss,
            BsFlexDisplayCss,
            BsFlexDirectionCss,
            BsFlexJustifyCss,
            BsSpacingCss,
            BsFlexAlignContentCss,
            css`
                bs-jumbotron {
                    margin-top: 15px;
                }
                div#jumbotron-buttons {
                    margin-bottom: 20px;
                }
                div#jumbotron-buttons bs-link-button {
                    margin-right: 20px;
                }
            `
        ];
    }

//  static get styles() {
  //  return css`
//      * {
//        font-family: sans-serif;
//      }
//      #container {
//        padding-top: ${HeaderHeight};
//        flex-grow: 1;
//        display: flex;
//      }
//      #container > * {
//        flex-grow: 1;
//      }
//      :host {
//        height: 100%;
//        display: flex;
//      }
//    `;
//  }
}
