import { customElement, LitElement, html, css } from 'lit-element';
import { from, Subscription } from 'rxjs';
import { API, Submission, Standing, implementsAccepted } from '../api';
import { router, session } from '../state';
import { format_datetime_detail } from '../utils';

@customElement('penguin-judge-contest-standings')
export class PenguinJudgeContestStandings extends LitElement {
    standings: Standing[] = [];

    subscription: Subscription | null = null;
    submissions: Submission[] = [];

    problems: string[] = [];

    constructor() {
        super();
        if (!session.contest || !session.contest.id) {
            throw 'あり得ないエラー';
        }
        this.subscription = from(API.get_standings(session.contest.id)).subscribe(
            standings => { this.standings = standings; },
            err => { console.log(err); router.navigate('login'); },
            () => { this.requestUpdate(); }
        );

        this.problems = session!.contest!.problems!.map((problem) => problem.id);
        console.log(this.problems);
        console.log(this.standings);
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        if (this.subscription) {
            this.subscription.unsubscribe();
            this.subscription = null;
        }
    }

    render() {
        const nodes: any[] = [];
        this.submissions.forEach((s) => {
            nodes.push(html`<tr><td>${format_datetime_detail(s.created)}</td><td>${s.problem_id}</td><td>${s.user_id}</td><td>${s.environment_id}</td><td>${s.status}</td></tr>`);
        });

        return html`
      <table>
        <thead>
            <tr>
                <td>順位</td>
                <td>ユーザ</td>
                <td>得点</td>
                ${this.problems.map(s => {
            if (session.contest && session.contest.id) {
                const taskURL = router.generate('contest-task', { id: session.contest.id, task_id: s });
                return html`<td><a href="${taskURL}">${s}</a></td>`;
            } else {
                return html`<td>${s}</td>`;
            }
        })}
            </tr>
        </thead>
        <tbody>${this.standings.map((user, i) => html`<tr>
            <td class="rank">${i + 1}</td>
            <td class="user-id">${user.user_id}</td>
            <td class="score-time">
                <p class="score">${user.score}</p>
                <p class="time">${user.adjusted_time}</p>        
            </td>
            ${
            this.problems.map(s => {
                const problem = user.problems[s];
                const score = implementsAccepted(problem) ? `${problem.score}` : '';
                const acceptedTime = implementsAccepted(problem) ? `${problem.time}` : '';
                const NotSubmitYet = !implementsAccepted(problem) && problem.penalties === 0;
                const penalties = NotSubmitYet ? '' : `(${problem.penalties})`;
                return html`
                    <p>
                        <span class="score">${score}</span>
                        <span class="penalties">${penalties}</span>
                    </p>
                    <p>
                        <span class="time">${acceptedTime}</span>
                    </p>
                    ${NotSubmitYet ? html`<p>-</p>` : ''}
                `;
            }).map(s => html`<td>${s}</td>`)
            }</tr>`)}</tbody>
      </table>`;
    }

    static get styles() {
        return css`
    table {
      border-collapse:collapse;
      margin: auto;
    }
    td {
      border: 1px solid #bbb;
      padding: 0.5ex 1ex;
      text-align: center;
    }
    thead td {
      font-weight: bold;
      text-align: center;
      min-width: 60px;
    }
    td > p {
        margin: 5px 0;
    }
    .user-id {
        font-weight: bold;
        min-width: 200px;
    }
    .score {
        font-weight: bold;
        color: #227D51;
    }
    .time {
        color: #B3ADA0;
    }
    .penalties {
        color: #CB1B45;
    }
    `;
    }
}
