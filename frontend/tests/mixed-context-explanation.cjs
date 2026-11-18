// Pure rendering; no browser session, server or user data is accessed.
const fs = require('node:fs'), path = require('node:path'), Module = require('node:module');
const assert = require('node:assert/strict'), ts = require('typescript');
const React = require('react'), { renderToStaticMarkup } = require('react-dom/server');
const filename = path.resolve(__dirname, '../components/MixedContextExplanation.tsx');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } });
const loaded = new Module(filename, module); loaded.filename = filename; loaded.paths = Module._nodeModulePaths(path.dirname(filename)); loaded._compile(compiled.outputText, filename);
const View = loaded.exports.default;
const render = value => renderToStaticMarkup(React.createElement(View, { value }));
assert.equal(render(undefined), '');
const value = { summary: { label: 'Shopping', assumptions: ['Ordinary shopping only.'], limits_note: 'Recorded appearance; no dress-code certification.' }, selection_mode: 'best_evidenced_with_coverage_v1', fallback_reason: null, global_optimum_certified: false, coverage: { unresolved_candidates: 1 } };
const html = render(value);
assert.match(html, /Context: Shopping/); assert.match(html, /mandatory garment conditions/); assert.match(html, /ranking remains uncertain/); assert.match(html, /no dress-code certification/);
assert.match(render({ ...value, selection_mode: 'baseline_disclosed_v1' }), /baseline ranking was retained among context-eligible outfits/);
console.log('PASS: context, provenance limitations, unresolved ranking and disclosed baseline; old results render no extra section.');
