import './anchor';
import './header';
import './home';
import './contests';
import './contest-top';
import './contest-tasks';
import './contest-task';
import { HeaderHeight } from './consts';
import { router, session } from './state';

import { customElement, LitElement, html, css, property } from 'lit-element';

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
      ['', 'home', html`<x-home></x-home>`, null],
    ];
    routes.forEach((v) => {
      const [path, name, body, before_hook] = v;
      let hooks = undefined;
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
    if (!path.startsWith('contests/'))
      session.leave_contest();
    session.task_id = params && params.hasOwnProperty('task_id') ? params['task_id'] : null;
    this.route = body;
  }

  private _wait_fetch_contest_info(done: any, params: {[key: string]: string}) {
    session.enter_contest(params.id).then(_ => done());
  }

  render() {
    return html`<x-header></x-header><div id="container">${this.route}</div>`
  }

  static get styles() {
    return css`#container { margin-top: ${HeaderHeight}; padding: 1ex; };`;
  }
}
