export interface Environment {
  id: number;
  name: string;
}

export interface Problem {
  id: string;
  title: string;
  description: string;
}

export interface Contest {
  id: string;
  title: string;
  description: string;
  problems: Array<Problem> | null;
}

export interface PartialSubmission {
  contest_id: string;
  problem_id: string;
  code: string;
  environment_id: string;
}

export interface Submission extends PartialSubmission {
  id: number;
  status: string;
  created: string;
}


export class API {
  static list_contests(): Promise<Array<Contest>> {
    return new Promise((resolve, reject) => {
      fetch('/api/contests').then((res) => {
        resolve(res.json());
      }).catch(reject);
    });
  }

  static get_contest(id: string): Promise<Contest> {
    return new Promise((resolve, reject) => {
      fetch('/api/contests/' + encodeURIComponent(id)).then((res) => {
        resolve(res.json());
      }).catch(reject);
    });
  }

  static list_environments(): Promise<Array<Environment>> {
    return new Promise((resolve, reject) => {
      fetch('/api/environments').then((res) => {
        resolve(res.json());
      }).catch(reject);
    });
  }

  static submit(submission: PartialSubmission): Promise<void> {
    const contest_id = submission.contest_id;
    const problem_id = submission.problem_id;
    delete submission.contest_id;
    delete submission.problem_id;
    const path = '/api/contests/' + encodeURIComponent(contest_id)
      + "/problems/" + encodeURIComponent(problem_id);
    const headers = {'Content-Type': 'application/json'};
    return new Promise((resolve, reject) => {
      fetch(path, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(submission)
      }).then(_ => {
        resolve();
      }).catch(reject);
    });
  }
}
