// Smoke test for the built payload: settings-style (5-arg) loader.
// Run: node settings-loader-test.js
'use strict';
const fs = require('fs');
const path = process.argv[2] || require('path').join(__dirname, '..', 'out', 'payload-built-live.js');
const src = fs.readFileSync(path, 'utf8');

const realLog = console.log.bind(console);
const logs = [];
console.log = (m) => { logs.push(String(m)); };

globalThis.__aniketosConfig = {
  space: '', caption: 'Emulators', label: 'Emulators',
  limit: 7771, icon: '', presence: '',
};

// --- fake webpack for the settings bundle (5-arg factory call) ---
const factories = {};
factories[0] = function (module, exports, require) { exports.entry = true; };
factories[945] = function (module, exports, require) {
  exports.Info = {
    getSystemSoftwareVersion: function () {
      return Promise.resolve({
        displayVersion: '26.01-12.60.00.06-00.00.00.0.1',
        prefixVersion: '12.600.006',
        foo: 'bar',
      });
    },
    getSystemSoftwareVersionSync: function () {
      return { displayVersion: 'real-sync', prefixVersion: '12.600.006' };
    },
  };
  exports.other = 1;
};
const cache = {};
const requireFn = function (id) { return cache[id] || (cache[id] = run(id)); };
requireFn.m = factories;
requireFn.c = cache;
function run(id) {
  const m = { i: id, exports: {} };
  cache[id] = m;
  // exactly like the settings runtime:
  // factory.call(exports, module, exports, require, factory)
  return factories[id].call(m.exports, m, m.exports, requireFn, factories[id]), m.exports;
}

eval(src);

run(0); // first factory call -> trap captures require, wraps all factories
run(945); // module 945 -> patchInfo should have fired

const Info = cache[945].exports.Info;

Promise.resolve(Info.getSystemSoftwareVersion()).then((v) => {
  const real = typeof realLog === 'function' ? realLog : console.log;
  const out = [];
  out.push('displayVersion = ' + v.displayVersion);
  out.push('prefixVersion = ' + v.prefixVersion + ' (must stay real)');
  out.push('foo = ' + v.foo + ' (must survive)');
  const s = Info.getSystemSoftwareVersionSync();
  out.push('sync displayVersion = ' + s.displayVersion);
  out.push('require captured (wrapped 945): ' + (factories[945] !== undefined));
  out.push('factory table wrapped: ' + (String(factories[945]).indexOf('function') >= 0));
  out.push('-logs-');
  logs.forEach((l) => out.push(l));
  process.stdout.write(out.join('\n') + '\n');
  process.exit(0);
}).catch((e) => {
  process.stdout.write('FAIL: ' + e + '\n');
  process.exit(1);
});
