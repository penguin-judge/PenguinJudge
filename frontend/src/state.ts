import Navigo from 'navigo';
import { BehaviorSubject } from 'rxjs';

import { API, Contest, Environment, User } from './api';

export const router: any = new Navigo(null, true, '#!');

interface NumKeyDictionary<T> {
  [index: number]: T;
}

class Session {
  // Path
  private _path = new BehaviorSubject<string>('/');
  navigated(path: string): void {
    this._path.next(path);
  }
  get path() {
    return this._path;
  }
  get current_path() {
    return this._path.value;
  }

  // Authentication
  private _user = new BehaviorSubject<User | null>(null);
  get current_user() { return this._user; }
  update_current_user() {
    API.get_current_user().then(user => {
      if (user)
        this._user.next(user);
    });
  }

  // Environment
  private _envs = new BehaviorSubject<Array<Environment>>([]);
  private _env_map = new BehaviorSubject<NumKeyDictionary<Environment>>({});
  get environment_subject() { return this._envs; }
  get environments() { return this._envs.value; }
  get environment_mapping_subject() { return this._env_map; }
  get environment_mapping() { return this._env_map.value; }

  // Contest
  private _contest = new BehaviorSubject<Contest | null>(null);
  enter_contest(id: string): Promise<Contest> {
    if (!id)
      throw 'BUG: context_id must not be null';
    return new Promise((resolve, reject) => {
      if (this.contest && this.contest.id === id) {
        resolve(this.contest);
        return;
      }
      API.get_contest(id).then((c) => {
        resolve(c);
        this._contest.next(c);
      }).catch(reject);
    });
  }
  leave_contest() {
    if (this.contest)
      this._contest.next(null);
  }
  get contest() {
    return this._contest.value;
  }
  get contest_subject() { return this._contest; }
  task_id: string | null = null;

  // Init
  init() {
    API.list_environments().then((envs) => {
      if (envs) {
        this._envs.next(envs);
        this._env_map.next(envs.reduce((obj: { [key: number]: Environment }, e) => {
          obj[e.id] = e;
          return obj;
        }, {}));
      }
    });
    this.update_current_user();
  }
}
export const session = new Session();
