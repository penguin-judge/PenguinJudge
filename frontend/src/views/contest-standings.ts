import { customElement, LitElement, html, css, TemplateResult } from 'lit-element';
import { API, Submission, Standing, implementsAccepted } from '../api';
import { router, session } from '../state';

@customElement('penguin-judge-contest-standings')
export class PenguinJudgeContestStandings extends LitElement {
    standings: Standing[] = [];

    submissions: Submission[] = [];

    problems: string[] = [];

    userPerPage = 20;
    page = 1;

    constructor() {
        super();
        if (!session.contest || !session.contest.id) {
            throw 'あり得ないエラー';
        }

        API.get_standings(session.contest.id).then(standings => {
            this.standings = standings;
            this.requestUpdate();
        }).catch(err => {
            console.log(err);
            router.navigate('login');
        })

        this.problems = session!.contest!.problems!.map((problem) => problem.id);
    }

    disconnectedCallback() {
        super.disconnectedCallback();
    }

    changePage(n: number): Function {
        return () => {
            this.page = n;
            this.requestUpdate();
        };
    }

    createPagenation(pageNum: number): Array<TemplateResult> {
        // TODO: 別コンポーネントに切り出す
        const isShowAllPage = pageNum <= 10;
        const index = this.page;
        const pages = [index];
        if (isShowAllPage) {
            for (let i = index - 1; i >= 1; --i) {
                pages.push(i);
            }
            pages.reverse();
            for (let i = index + 1; i <= pageNum; ++i) {
                pages.push(i);
            }
        } else {
            for (let i = 2; index - i >= 1; i *= 2) {
                pages.push(index - (i - 1));
            }
            if (index > 1) pages.push(1);
            pages.reverse();

            for (let i = 2; index + i <= pageNum; i *= 2) {
                pages.push(index + (i - 1));
            }
            if (index < pageNum) pages.push(pageNum);
        }
        const pagenation = pages.map(i => {
            const isCurrentPage = i === index;
            return html`<button class="page ${isCurrentPage ? 'disable' : ''}" @click="${this.changePage(i)}">${i}</button>`;
        });

        return pagenation;
    }

    render() {
        const pageNum = Math.floor((this.standings.length + this.userPerPage - 1) / this.userPerPage);
        const index = this.page;

        const pagenation = this.createPagenation(pageNum);

        const isInCurrentPage = (i: number) => i >= ((index - 1) * this.userPerPage) && i < (index * this.userPerPage);

        return html`
        <div class="pagenation">${pagenation}</div>
        <table id="standings">
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
                <div class="score">${user.score}</div>
                <div class="time">${user.adjusted_time}</div>        
            </td>
            ${
            this.problems.map(s => {
                const problem = user.problems[s];
                const NotSubmitYet = !implementsAccepted(problem) && problem.penalties === 0;
                if (NotSubmitYet) return html`<div>-</div>`;

                const score = implementsAccepted(problem) ? `${problem.score}` : '';
                const acceptedTime = implementsAccepted(problem) ? `${problem.time}` : '';
                const penalties = problem.penalties;
                return html`
                    <div>
                        <span class="score">${score}</span>
                        <span class="penalties">${penalties}</span>
                    </div>
                    <div>
                        <span class="time">${acceptedTime}</span>
                    </div>
                `;
            }).map(s => html`<td>${s}</td>`)
            }</tr>`)}</tbody>
        </table>
        `;
    }

    static get styles() {
        return css`
    #standings {
      border-collapse:collapse;
      margin: auto;
    }
    #standings a {
        color: #005CAF;
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
        width: 32px;
        height: 32px;
        margin: 4px;
        text-align: center;
        vertical-align: middle;
        background-color: white;
    }
    .page.disable {
        opacity: 0.5;
        pointer-events: none;
    }
    `;
    }
}
