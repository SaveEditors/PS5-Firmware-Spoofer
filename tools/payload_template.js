(function () {
  var cfg = globalThis.__aniketosConfig || {};
  if (globalThis.__aniketos) return;
  var A = globalThis.__aniketos = { patched: {}, errors: 0 };
  var SPACE = cfg.space;
  var VER = '__FAKE_VERSION__';
  var LIVE = '__LIVE_URL__';
  function log(m) {
    try {
      console.log(m.charAt(0) === ':' ? 'ANIKETOS' + m : 'ANIKETOS ' + m);
    } catch (e) {}
  }
  function once(name, id) {
    if (A.patched[name]) return false;
    A.patched[name] = id;
    log('patched ' + name + ' in module ' + id);
    return true;
  }

  /* Proof of life for the injection watchdog: fires early, before the
     riskier install work below, so a fault further down still confirms. */
  setTimeout(function () {
    log('alive early');
  }, 1500);

  /* Games space accessor: swaps the filter space for the native one. */
  function wrapAccessor(accessor, id) {
    var original = accessor.setSearchCondition;
    if (typeof original !== 'function' || original.__aniketos) return;
    var wrapped = function (ctxId, condition) {
      if (condition && condition.filterTypeDispLocationSpace === SPACE) {
        var copy = {};
        for (var key in condition) copy[key] = condition[key];
        copy.filterTypeDispLocationSpace = 'game';
        copy.contentLimit = cfg.limit;
        arguments[1] = copy;
      }
      return original.apply(this, arguments);
    };
    wrapped.__aniketos = true;
    try {
      accessor.setSearchCondition = wrapped;
      once('AppBrowseItemAccessor.setSearchCondition', id);
    } catch (e) { log('accessor not writable: ' + e); }
  }
  function patchObject(o, id) {
    if (!SPACE || !o || (typeof o !== 'object' && typeof o !== 'function'))
      return;
    var ids = o.spaceIds;
    if (Array.isArray(ids) && ids.indexOf('game') >= 0 &&
        ids.indexOf(SPACE) < 0) {
      ids.push(SPACE);
      once('spaceIds', id);
    }
    var text = o.textBySpaceId;
    if (text && typeof text === 'object' && !(SPACE in text)) {
      text[SPACE] = cfg.caption;
      once('textBySpaceId', id);
    }
    var labels = o.accessibilityLabelsBySpaceId;
    if (labels && typeof labels === 'object' && !(SPACE in labels)) {
      labels[SPACE] = cfg.label;
      once('accessibilityLabelsBySpaceId', id);
    }
    var accessor = o.AppBrowseItemAccessor;
    if (accessor && typeof accessor === 'object') wrapAccessor(accessor, id);
  }

  /* Top bar: Search replaced by original + our button (cfg.icon). */
  function findReact(o) {
    if (!A.React && o && typeof o.createElement === 'function' &&
        typeof o.memo === 'function' && o.Fragment) A.React = o;
  }
  function patchIcons(o, id) {
    if (!cfg.icon || A.patched.icon || !o) return;
    var Search = o.Search;
    if (!Search || !o.Settings || !o.Profile) return;
    var inner = typeof Search === 'function' ? Search : Search.type;
    if (typeof inner !== 'function') return;
    var press = function () { log(':menu'); };
    var Both = function (props) {
      var search = inner(props || {});
      var React = A.React;
      if (!cfg.icon || !React || !search || !search.type) return search;
      var own = {};
      for (var key in search.props) own[key] = search.props[key];
      own.iconId = { uri: cfg.icon };
      own.onPress = press;
      own.title = '';
      own.key = 'aniketos';
      return React.createElement(React.Fragment, null, search,
          React.createElement(search.type, own));
    };
    var replacement = A.React ? A.React.memo(Both) : Both;
    try {
      o.Search = replacement;
    } catch (e) {}
    if (o.Search !== replacement) {
      try {
        Object.defineProperty(o, 'Search', {
          enumerable: true, configurable: true,
          get: function () { return replacement; }
        });
      } catch (e) { log('Search not replaceable: ' + e); return; }
    }
    if (o.Search === replacement) once('icon', id);
  }

  /* Presence dots (cfg.presence). */
  function patchLamps(o, id) {
    var table = o && o.default;
    if (A.patched.lamps || !table || typeof table !== 'object' ||
        !table.online || !table.busy || !table.appearOffline ||
        !('unavailable' in table) || !table.online.iconId) return;
    if (typeof Proxy !== 'function') { log('lamps: no Proxy'); return; }
    var view = new Proxy(table, {
      get: function (target, key) {
        var forced = cfg.presence && target[cfg.presence];
        if (forced && (key === 'none' || key === 'unavailable' ||
                       key === 'appearOffline'))
          return forced;
        return target[key];
      }
    });
    try { o.default = view; } catch (e) {}
    if (o.default !== view) {
      try {
        Object.defineProperty(o, 'default', {
          enumerable: true, configurable: true,
          get: function () { return view; }
        });
      } catch (e) { log('lamps not replaceable: ' + e); return; }
    }
    if (o.default === view) once('lamps', id);
  }

  /* System Information version: wraps the static methods of the Info export
     wherever the module is (class or namespace object, data property or
     getter). The firmware number inside the real displayVersion string
     ('12.60') is swapped for the fake version - same length and format, the
     rest of the string stays real. If the token is absent the whole field
     falls back to the fake version. The real prefixVersion is kept and the
     first swap is logged. */
  function patchInfo(exports, id) {
    if (!exports) return;
    var info = null;
    try {
      var d = Object.getOwnPropertyDescriptor(exports, 'Info');
      if (d) {
        if (d.value) info = d.value;
        else if (typeof d.get === 'function') info = d.get.call(exports);
      }
      if (!info) info = exports.Info;
    } catch (e) {}
    if (!info || (typeof info !== 'object' && typeof info !== 'function') ||
        info.__aniketosVersion) return;
    var async = info.getSystemSoftwareVersion;
    if (typeof async !== 'function') return;
    var sync = info.getSystemSoftwareVersionSync;
    var fix = function (value) {
      if (!value || typeof value !== 'object') return value;
      var out = {};
      for (var key in value) out[key] = value[key];
      var dv = '' + out.displayVersion;
      out.displayVersion = dv.indexOf('12.60') < 0 ? VER
        : dv.replace('12.60', VER);
      if (!A.orig) {
        A.orig = 1;
        log('orig ' + dv + ' -> ' + out.displayVersion);
      }
      return out;
    };
    var put = function (name, fn) {
      try { info[name] = fn; } catch (e) {}
      if (info[name] !== fn) {
        try {
          Object.defineProperty(info, name, {
            value: fn, writable: true, configurable: true
          });
        } catch (e) {}
      }
      return info[name] === fn;
    };
    var ok = put('getSystemSoftwareVersion', function () {
      var result = async.apply(this, arguments);
      return result && typeof result.then === 'function' ? result.then(fix)
        : fix(result);
    });
    if (!ok) {
      A.errors++;
      log('version not replaceable in module ' + id);
      return;
    }
    if (typeof sync === 'function') {
      put('getSystemSoftwareVersionSync', function () {
        return fix(sync.apply(this, arguments));
      });
    }
    info.__aniketosVersion = VER;
    log('version ' + VER + ' in module ' + id);
    startPoll();
  }

  function patchModule(module, id) {
    try {
      var exports = module && module.exports;
      if (!exports) return;
      if (SPACE) {
        findReact(exports);
        if (exports.default) findReact(exports.default);
        patchIcons(exports, id);
        patchLamps(exports, id);
        patchObject(exports, id);
        if (exports.default) patchObject(exports.default, id);
      }
      patchInfo(exports, id);
    } catch (e) {
      A.errors++;
      log('error in module ' + id + ': ' + e);
    }
  }

  /* webpack's require is private. It shows once per bundle in the call that
     runs a module: factory.call(module.exports, module, module.exports,
     require) - home - or with the factory appended - settings. The first
     such call hands over require (factories require.m, cache require.c):
     the cache is patched right away (modules that already ran) and the
     factory table is wrapped (modules still to come, reloads included).
     The trap stays live so a reloaded bundle hands over its table too. */
  var originalCall = Function.prototype.call;
  var seen = [];
  function hookRequire(require) {
    var factories = require.m;
    var cache = require.c;
    var count = 0;
    var wrap = function (factory, id) {
      return function (module, exports, req, factoryRef) {
        var result = factory.call(this, module, exports, req, factoryRef);
        patchModule(module, id);
        return result;
      };
    };
    for (var id in factories) {
      if (typeof factories[id] === 'function') {
        factories[id] = wrap(factories[id], id);
        count++;
      }
    }
    if (cache) {
      for (var cid in cache) {
        try { patchModule(cache[cid], cid); } catch (e) {}
      }
    }
    log('webpack require captured, ' + count + ' modules');
  }
  Function.prototype.call = function () {
    var module = arguments[1];
    var req = arguments[3];
    if ((arguments.length === 4 || arguments.length === 5) &&
        typeof req === 'function' && req.m && req.c &&
        module && typeof module === 'object' &&
        module.exports === arguments[0] && arguments[0] === arguments[2] &&
        seen.indexOf(req) < 0) {
      seen.push(req);
      try { hookRequire(req); } catch (e) { log('hook failed: ' + e); }
      var result = originalCall.apply(this, arguments);
      patchModule(module, module.i === undefined ? 'entry' : module.i);
      return result;
    }
    return originalCall.apply(this, arguments);
  };

  /* Live value: starts as soon as the settings bundle (the only one with the
     Info module) is patched; every 2.5 s the PC is asked for a new value.
     Failures keep VER. */
  var pollStarted = false;
  function poll() {
    try {
      var x = new XMLHttpRequest();
      x.open('GET', LIVE + '?x=' + Date.now(), true);
      x.timeout = 3000;
      x.onload = function () {
        var t = (x.responseText || '').replace(/^\s+|\s+$/g, '');
        if (t && t.length < 64 && t !== VER) {
          VER = t;
          log('version <- ' + t);
        }
      };
      x.send(null);
    } catch (e) {}
  }
  function startPoll() {
    if (!LIVE || pollStarted) return;
    pollStarted = true;
    setInterval(poll, 2500);
    setTimeout(poll, 300);
  }

  setTimeout(function () {
    log('alive patched=' + JSON.stringify(A.patched) + ' errors=' + A.errors +
        ' hooks=' + seen.length);
  }, 8000);
  log('installed for space ' + SPACE);
})();
