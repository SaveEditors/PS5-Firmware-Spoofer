// Smoke test for the built payload: home-style (4-arg) loader.
// Verifies the original home patches still work: spaceIds/caption/label,
// accessor swap, top-bar icon, presence lamps.
'use strict';
const fs = require('fs');
const src = fs.readFileSync(process.argv[2] || require('path').join(__dirname, '..', 'out', 'payload-built-live.js'), 'utf8');
const logs = [];
console.log = (m) => { logs.push(String(m)); };
globalThis.__aniketosConfig = {
  space: 'emulators', caption: 'Emulators', label: 'Emulators label',
  limit: 7771, icon: 'file:///data/AniketosHEN/menu.png', presence: 'online',
};

const factories = {};
// module 0: React-like
factories[0] = function (module, exports, require) {
  exports.createElement = function (type, props) {
    return { type: type, props: props || {}, children: Array.prototype.slice.call(arguments, 2) };
  };
  exports.memo = function (f) { return f; };
  exports.Fragment = 'Fragment';
};
// module 1: top-bar icons
const Search = function (props) { return { type: 'SearchIcon', props: props || {} }; };
factories[1] = function (module, exports, require) {
  exports.Search = Search;
  exports.Settings = function () {};
  exports.Profile = function () {};
};
// module 2: data tables + accessor
const accessorCalls = [];
factories[2] = function (module, exports, require) {
  exports.spaceIds = ['game'];
  exports.textBySpaceId = { game: 'Games' };
  exports.accessibilityLabelsBySpaceId = { game: 'Games label' };
  exports.AppBrowseItemAccessor = {
    setSearchCondition: function (ctx, cond) { accessorCalls.push(cond); return 'ok'; },
  };
};
// module 3: presence lamps
factories[3] = function (module, exports, require) {
  exports.default = {
    online: { iconId: 'online.png' },
    busy: { iconId: 'busy.png' },
    appearOffline: { iconId: 'offline.png' },
    unavailable: { iconId: 'unavail.png' },
    none: { iconId: 'none.png' },
  };
};
const cache = {};
const requireFn = function (id) { return cache[id] || (cache[id] = run(id)); };
requireFn.m = factories;
requireFn.c = cache;
function run(id) {
  const m = { i: id, exports: {} };
  cache[id] = m;
  factories[id].call(m.exports, m, m.exports, requireFn); // HOME style: 4 args
  return m.exports;
}

eval(src);
[0, 1, 2, 3].forEach(run);

const out = [];
const m1 = cache[1].exports;
const m2 = cache[2].exports;
const m3 = cache[3].exports.default;

out.push('spaceIds = ' + JSON.stringify(m2.spaceIds));
out.push('text[emulators] = ' + m2.textBySpaceId.emulators);
out.push('label[emulators] = ' + m2.accessibilityLabelsBySpaceId.emulators);

m2.AppBrowseItemAccessor.setSearchCondition(1, { filterTypeDispLocationSpace: 'emulators', q: 'x' });
m2.AppBrowseItemAccessor.setSearchCondition(1, { filterTypeDispLocationSpace: 'game' });
out.push('accessor calls = ' + JSON.stringify(accessorCalls));

out.push('Search replaced = ' + (m1.Search !== Search));
const node = m1.Search({});
const btn = node.children && node.children[1];
out.push('extra button icon = ' + JSON.stringify(btn && btn.props.iconId));

out.push('lamp none -> ' + JSON.stringify(m3.none));
out.push('lamp appearOffline -> ' + JSON.stringify(m3.appearOffline));
out.push('lamp busy (untouched) -> ' + JSON.stringify(m3.busy));

out.push('-logs-');
logs.forEach((l) => out.push(l));
process.stdout.write(out.join('\n') + '\n');
process.exit(0);
