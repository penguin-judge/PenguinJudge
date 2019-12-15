export interface User {
  id: string;
  name: string;
  admin: boolean;
  created: string;
}

export interface Environment {
  id: number;
  name: string;
}

export interface Problem {
  id: string;
  title: string;
  description: string;
  time_limit: number;
  memory_limit: number;
  score: number;
}

export interface Contest {
  id: string;
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  published: boolean;
  problems?: Array<Problem> | null;
}

export enum JudgeStatus {
  Waiting = 'Waiting',
  Running = 'Running',
  Accepted = 'Accepted',
  CompilationError = 'CompilationError',
  RuntimeError = 'RuntimeError',
  WrongAnswer = 'WrongAnswer',
  MemoryLimitExceeded = 'MemoryLimitExceeded',
  TimeLimitExceeded = 'TimeLimitExceeded',
  OutputLimitExceeded = 'OutputLimitExceeded',
  InternalError = 'InternalError',
}

export interface PartialSubmission {
  contest_id: string;
  problem_id: string;
  code: string;
  environment_id: number;
}

export interface Submission extends PartialSubmission {
  id: number;
  status: string;
  created: string;
  user_id: string;
  tests: Array<TestResult>;
}

export interface TestResult {
  id: string;
  status: JudgeStatus;
  time: number | null;
  memory: number | null;
}

export interface Token {
  token: string;
  expires_in: number;
}

interface AcceptedProblem {
  penalties: number;
  score: number;
  time: number;
}

interface UnacceptedProblem {
  penalties: number;
}

export function implementsAccepted(arg: any): arg is AcceptedProblem {
  return arg !== null && typeof arg === 'object' && arg.score !== undefined && arg.time !== undefined;
}

export interface Standing {
  user_id: string;
  score: number;
  penalties: number;
  time: number;
  adjusted_time: number;
  ranking: number;
  problems: {
    [index: string]: AcceptedProblem | UnacceptedProblem;
  }
}

export interface ListContestsFilter {
  status?: string;
}

export class API {
  private static _fetch<T>(url: string, init?: RequestInit): Promise<T> {
    // 以下の情報を返却するPromiseを返す
    // [成功した場合]
    //   <jsonパース成功> resolve(T)
    //   <jsonパース失敗> reject(undefined)
    // [サーバからエラーが返却された場合]
    //   reject({status: HTTPステータスコード, json: bodyが含まれる場合})
    // [サーバとの通信が切断された場合]
    //   reject(undefined)
    return new Promise((resolve, reject) => {
      fetch(url, init).then(resp => {
        if (resp.ok) {
          resp.json().then(resolve).catch(_ => reject(undefined));
        } else {
          resp.json().then(body => {
            reject({ status: resp.status, json: body });
          }, _ => {
            reject({ status: resp.status, json: undefined });
          });
        }
      }, _ => {
        reject(undefined);
      });
    });
  }

  static get_current_user(): Promise<User> {
    return API._fetch('/api/user');
  }

  static list_contests(filter?: ListContestsFilter): Promise<Array<Contest>> {
    let q = '';
    if (filter) {
      let tmp = [];
      if (filter.status)
        tmp.push('status=' + encodeURIComponent(filter.status))
      if (tmp)
        q = '?' + tmp.join('&');
    }
    return API._fetch('/api/contests' + q);
  }

  static get_contest(id: string): Promise<Contest> {
    return API._fetch('/api/contests/' + encodeURIComponent(id));
  }

  static list_environments(): Promise<Array<Environment>> {
    return API._fetch('/api/environments');
  }

  static submit(submission: PartialSubmission): Promise<Submission> {
    const contest_id = submission.contest_id;
    delete submission.contest_id;
    const path = '/api/contests/' + encodeURIComponent(contest_id) + '/submissions';
    return API._fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submission)
    });
  }

  static list_submissions(contest_id: string): Promise<Array<Submission>> {
    return API._fetch(
      '/api/contests/' + encodeURIComponent(contest_id) + '/submissions');
  }

  static get_submission(contest_id: string, submission_id: string): Promise<Submission> {
    return API._fetch(
      '/api/contests/' + encodeURIComponent(contest_id) +
      '/submissions/' + encodeURIComponent(submission_id));
  }

  static login(id: string, password: string): Promise<Token> {
    return API._fetch('/api/auth', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id,
        password,
      })
    });
  }

  static get_standings(contest_id: string): Promise<Array<Standing>> {
    return API._fetch(`/api/contests/${contest_id}/rankings`);
  }

  static create_contest(contest: Contest): Promise<Contest> {
    return API._fetch('/api/contests', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(contest),
    });
  }

  static update_contest(contest_id: string, patch: any): Promise<Contest> {
    return API._fetch('/api/contests/' + encodeURIComponent(contest_id), {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch),
    });
  }
}
