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
const message='This outfit was recommended using a default smart-casual style because no dress code was specified. If your interview requires a different dress code, start a new chat and include the required dress code in your request.';
const base={summary:{label:'Job interview',assumptions:[]},selection_mode:'baseline_disclosed_v1',fallback_reason:'objective_unavailable'};
const initial={...base,interview_default:{inferred:true,message,origin:'approved_policy_default',verified_dress_code:false}};
assert.ok(render(initial).includes(message));
const historical=JSON.parse(JSON.stringify(initial));assert.ok(render(historical).includes(message));
assert.ok(!render({...base,interview_default:{inferred:false,message:null,origin:'user_specified',verified_dress_code:false}}).includes(message));
assert.ok(!render(base).includes(message));
console.log('PASS: exact inferred-default message on current and historical results; explicit and old results unchanged.');
