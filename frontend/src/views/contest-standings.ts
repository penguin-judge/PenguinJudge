import { customElement, LitElement, html, css } from 'lit-element';
import { from, Subscription } from 'rxjs';
import { API, Submission, Standing, implementsAccepted } from '../api';
import { router, session } from '../state';

@customElement('penguin-judge-contest-standings')
export class PenguinJudgeContestStandings extends LitElement {
    standings: Standing[] = [];

    subscription: Subscription | null = null;
    submissions: Submission[] = [];

    problems: string[] = [];

    userPerPage = 20;
    page = 1;

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

    changePage(n: number): Function {
        return () => {
            this.page = n;
            this.requestUpdate();
        };
    }

    render() {
        const pageNum = Math.floor((this.standings.length + this.userPerPage - 1) / this.userPerPage);
        const pages = [this.page];
        const index = this.page;

        for (let i = 2; index - i >= 1; i *= 2) {
            pages.push(index - (i - 1));
        }
        if (index > 1) pages.push(1);
        pages.reverse();

        for (let i = 2; index + i <= pageNum; i *= 2) {
            pages.push(index + (i - 1));
        }
        if (index < pageNum) pages.push(pageNum);

        const pagenation = pages.map(i => {
            const isCurrentPage = i === index;
            return html`<button class="page ${isCurrentPage ? 'disable' : ''}" @click="${this.changePage(i)}">${i}</button>`;
        });

        const isInCurrentPage = (i: number) => i >= ((index - 1) * this.userPerPage) && i < (index * this.userPerPage);

        return html`
        <div class="pagenation">${pagenation}</div>
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
        <tbody>${this.standings.filter((_, i) => isInCurrentPage(i)).map((user) => html`<tr>
            <td class="rank">${user.ranking}</td>
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
        </table>
        `;
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
    .pagenation {
        max-width: 600px;
        margin: auto;
        padding: 10px;
        display: flex;
        justify-content: center;
    }
    .page {
        border: 1px solid black;
        width: 40px;
        height: 40px;
        margin: 4px;
        text-align: center;
        vertical-align: middle;
    }
    .page.disable {
        opacity: 0.5;
        pointer-events: none;
    }
    `;
    }
}
