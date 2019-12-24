import { LitElement, customElement, html, css } from 'lit-element';

@customElement('x-ace-editor')
export class AceEditor extends LitElement {
  _editor: AceAjax.Editor | null = null;

  render() {
    return html`<div id="editor"></div>`;
  }

  get value(): string {
    return this._editor!.getValue();
  }

  get editor(): AceAjax.Editor | null {
    return this._editor;
  }

  setModeFromAmbiguous(name: string) {
    if (!this._editor)
      return;
    let mode_name: string | null = null
    name = name.toLowerCase().split(' ')[0];
    do {
      if (VALID_MODES.includes(name)) {
        mode_name = name;
        break
      }
      if (name === 'c' || name.startsWith('c++')) {
        mode_name = 'c_cpp';
        break
      }
      mode_name = 'text';
    } while (false);
    this._editor.session.setMode('ace/mode/' + mode_name);
  }

  updated(changedProperties: any) {
    super.updated(changedProperties);
    if (!this.shadowRoot || !ace || this._editor)
      return;
    const editor = this.shadowRoot.getElementById('editor');
    if (!editor)
      return;
    this._editor = ace.edit(editor);
    this._editor.setOptions({
      fontSize: '1em',
      setAutoScrollEditorIntoView: true,
    });
    // @ts-ignore
    this._editor.renderer.attachToShadowRoot();
    this._editor.resize();
  }

  static get styles() {
    return css`
    :host {
      display: flex;
    }
    div {
      flex-grow: 1;
    }
    `;
  }
}

const VALID_MODES = ['abap', 'abc', 'actionscript', 'ada', 'apache_conf', 'apex', 'applescript', 'aql', 'asciidoc', 'asl', 'assembly_x86', 'autohotkey', 'batchfile', 'bro', 'c9search', 'c_cpp', 'cirru', 'clojure', 'cobol', 'coffee', 'coldfusion', 'crystal', 'csharp', 'csound_document', 'csound_orchestra', 'csound_score', 'csp', 'css', 'curly', 'd', 'dart', 'diff', 'django', 'dockerfile', 'dot', 'drools', 'edifact', 'eiffel', 'ejs', 'elixir', 'elm', 'erlang', 'forth', 'fortran', 'fsharp', 'fsl', 'ftl', 'gcode', 'gherkin', 'gitignore', 'glsl', 'gobstones', 'golang', 'graphqlschema', 'groovy', 'haml', 'handlebars', 'haskell', 'haskell_cabal', 'haxe', 'hjson', 'html', 'html_elixir', 'html_ruby', 'ini', 'io', 'jack', 'jade', 'java', 'javascript', 'json', 'jsoniq', 'jsp', 'jssm', 'jsx', 'julia', 'kotlin', 'latex', 'less', 'liquid', 'lisp', 'livescript', 'logiql', 'logtalk', 'lsl', 'lua', 'luapage', 'lucene', 'makefile', 'markdown', 'mask', 'matlab', 'maze', 'mel', 'mixal', 'mushcode', 'mysql', 'nginx', 'nim', 'nix', 'nsis', 'objectivec', 'ocaml', 'pascal', 'perl', 'perl6', 'pgsql', 'php', 'php_laravel_blade', 'pig', 'plain_text', 'powershell', 'praat', 'prolog', 'properties', 'protobuf', 'puppet', 'python', 'r', 'razor', 'rdoc', 'red', 'redshift', 'rhtml', 'rst', 'ruby', 'rust', 'sass', 'scad', 'scala', 'scheme', 'scss', 'sh', 'sjs', 'slim', 'smarty', 'snippets', 'soy_template', 'space', 'sparql', 'sql', 'sqlserver', 'stylus', 'svg', 'swift', 'tcl', 'terraform', 'tex', 'text', 'textile', 'toml', 'tsx', 'turtle', 'twig', 'typescript', 'vala', 'vbscript', 'velocity', 'verilog', 'vhdl', 'visualforce', 'wollok', 'xml', 'xquery', 'yaml', 'zeek'];
