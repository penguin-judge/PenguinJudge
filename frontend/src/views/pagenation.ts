import { customElement, LitElement, html, css, TemplateResult } from 'lit-element';

@customElement('penguin-judge-pagenation')
export class PenguinJudgePagenation extends LitElement {
    static get properties() {
        return {
            pages: { type: Number },
            currentPage: { type: Number },
        };
    }

    pages: number;
    currentPage: number;

    constructor() {
        super();
        this.pages = 0;
        this.currentPage = 0;
    }

    dispatchPageChanged(n: number) {
        return () => this.dispatchEvent(new CustomEvent('page-changed', { detail: n }));
    }

    createPagenation(): Array<TemplateResult> {
        const isShowAllPage = this.pages <= 10;
        const index = this.currentPage;
        const pagenations = [index];
        if (isShowAllPage) {
            for (let i = index - 1; i >= 1; --i) {
                pagenations.push(i);
            }
            pagenations.reverse();
            for (let i = index + 1; i <= this.pages; ++i) {
                pagenations.push(i);
            }
        } else {
            for (let i = 2; index - i >= 1; i *= 2) {
                pagenations.push(index - (i - 1));
            }
            if (index > 1) pagenations.push(1);
            pagenations.reverse();

            for (let i = 2; index + i <= this.pages; i *= 2) {
                pagenations.push(index + (i - 1));
            }
            if (index < this.pages) pagenations.push(this.pages);
        }
        const pagenation = pagenations.map(i => {
            const isCurrentPage = i === index;
            return html`<button class="page${isCurrentPage ? ' disable' : ''}" @click="${this.dispatchPageChanged(i)}" value="${i}">${i}</button>`;
        });

        return pagenation;
    }

    render() {
        const pagenation = this.createPagenation();

        return html`
        <div class="pagenation">${pagenation}</div>
        `;
    }

    static get styles() {
        return css`
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
        /*pointer-events: none;*/
    }
    `;
    }
}
