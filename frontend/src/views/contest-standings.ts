import { customElement, LitElement, html, css } from 'lit-element';
import { API, Submission, Standing, implementsAccepted } from '../api';
import { router, session } from '../state';
import './pagenation';

const formatElapsedTime = (time: number) => {
    time = Math.floor(time);
    const minutes = Math.floor(time / 60);
    const seconds = time % 60;
    return `${`${minutes}`.padStart(2, '0')}:${`${seconds}`.padStart(2, '0')}`;
}

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
        if (!session.contest.problems) {
            // コンテスト開催前等で問題情報が読み込めていない
            return;
        }

        API.get_standings(session.contest.id).then(standings => {
            this.standings = standings;
            this.requestUpdate();
        }).catch(err => {
            console.log(err);
        })

        this.problems = session!.contest!.problems!.map((problem) => problem.id);
    }

    changePage(e: CustomEvent) {
        this.page = e.detail;
        this.requestUpdate();
    }

    render() {
        if (this.problems.length == 0) {
            return html`<div>コンテスト開催前です</div>`;
        }

        const pageNum = Math.floor((this.standings.length + this.userPerPage - 1) / this.userPerPage);
        const index = this.page;

        const isInCurrentPage = (i: number) => i >= ((index - 1) * this.userPerPage) && i < (index * this.userPerPage);

        return html`
        <penguin-judge-pagenation pages="${pageNum}" currentPage="${index}" @page-changed="${this.changePage}"></penguin-judge-pagenation>
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
                <div class="time">${formatElapsedTime(user.adjusted_time)}</div>        
            </td>
            ${
            this.problems.map(s => {
                const problem = user.problems[s];
                const NotSubmitYet = problem == undefined || (!implementsAccepted(problem) && problem.penalties === 0);
                if (NotSubmitYet) return html`<div>-</div>`;

                const score = implementsAccepted(problem) ? `${problem.score}` : '';
                const acceptedTime = implementsAccepted(problem) ? `${formatElapsedTime(problem.time)}` : '';
                const penalties = problem.penalties > 0 ? `(${problem.penalties})` : '';
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
