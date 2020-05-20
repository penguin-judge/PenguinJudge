import '@vanillawc/wc-markdown';

import './views/header';
import './views/home';
import './views/login';
import './views/logout';
import './views/register';
import './views/admin-environments';
import './views/admin-status';
import './views/contests';
import './views/contest-new';
import './views/contest-frame';
import './views/contest-top';
import './views/contest-tasks';
import './views/contest-task';
import './views/contest-task-new';
import './views/contest-task-edit';
import './views/contest-submission-results';
import './views/contest-submission';
import './views/contest-standings';
import './views/profile';
import './components/ace';
import './components/anchor';
import './components/contest-list';
import './components/icon';
import './components/panel';
import './components/dropdown-menu';
import { HeaderHeight } from './views/consts';
import { router, session } from './state';

import { customElement, LitElement, html, css, property } from 'lit-element';

@customElement('x-root')
export class AppRootElement extends LitElement {
  @property({ type: Object }) route = html``;

  constructor() {
    super();
    session.init();

    const routes: Array<[string, string, any, any]> = [
      ['contests', 'contests', html`<x-contests></x-contests>`, null],
      ['contests/~new', 'contest-new', html`<x-contest-new></x-contest-new>`, null],
      ['contests/:id', 'contest-top', html`<x-contest-top></x-contest-top>`, this._wait_fetch_contest_info],
      ['contests/:id/tasks', 'contest-tasks', html`<x-contest-tasks></x-contest-tasks>`, this._wait_fetch_contest_info],
      ['contests/:id/tasks/~new', 'contest-task-new', html`<x-contest-task-new></x-contest-task-new>`, this._wait_fetch_contest_info],
      ['contests/:id/tasks/:task_id', 'contest-task', html`<x-contest-task></x-contest-task>`, this._wait_fetch_contest_info],
      ['contests/:id/tasks/:task_id/edit', 'contest-task-edit', html`<x-contest-task-edit></x-contest-task-edit>`, this._wait_fetch_contest_info],
      ['contests/:id/submissions', 'contest-submissions', html`<penguin-judge-contest-submission-results />`, this._wait_fetch_contest_info],
      ['contests/:id/submissions/:submission_id', 'contest-submission', html`<penguin-judge-contest-submission />`, this._wait_fetch_contest_info],
      ['contests/:id/standings', 'contest-standings', html`<penguin-judge-contest-standings />`, this._wait_fetch_contest_info],
      ['login', 'login', html`<x-login></x-login>`, null],
      ['logout', 'logout', html`<x-logout></x-logout>`, null],
      ['register', 'register', html`<x-register></x-register>`, null],
      ['profile', 'profile', html`<x-profile></x-profile>`, null],
      ['admin/environments', 'admin-environments', html`<x-admin-environments></x-admin-environments>`, null],
      ['admin/status', 'admin-status', html`<x-admin-status></x-admin-status>`, null],
      ['', 'home', html`<x-home></x-home>`, null],
    ];
    routes.forEach((v) => {
      const [path, name, body, before_hook] = v;
      let hooks = undefined;
      if (before_hook) {
        hooks = { before: before_hook };
      }
      router.on(path, {
        as: name, uses: (params: { [key: string]: string }) => {
          this._route_handler(path, body, params);
        }
      }, hooks);
    });
    router.notFound((_: any) => {
      this.route = html`<h1>HTTP 404: NOT FOUND</h1>`
    });
    router.resolve();
  }

  private _route_handler(path: string, body: any, params: { [key: string]: string }) {
    if (path.startsWith('contests/') && params) {
      body = html`<penguin-judge-contest-frame>${body}</penguin-judge-contest-frame>`;
    } else {
      session.leave_contest();
    }
    session.task_id = params && params.hasOwnProperty('task_id') ? params['task_id'] : null;
    this.route = body;
    session.navigated(path);
  }

  private _wait_fetch_contest_info(done: any, params: { [key: string]: string }) {
    session.enter_contest(params.id).then(_ => done());
  }

  render() {
    return html`<penguin-judge-header></penguin-judge-header><div id="container">${this.route}</div>`
  }

  static get styles() {
    return css`
      * {
        font-family: sans-serif;
      }
      penguin-judge-header {
        z-index: 1;
      }
      #container {
        padding-top: ${HeaderHeight};
        flex-grow: 1;
        display: flex;
        z-index: 0;
      }
      #container > * {
        flex-grow: 1;
      }
      :host {
        height: 100%;
        display: flex;
      }
    `;
  }
}
