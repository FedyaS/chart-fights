/**
 * Browser-like verification with chart mock (Node-safe).
 */
const { readFileSync, writeFileSync, mkdirSync } = require('fs');
const { join, dirname } = require('path');
const Module = require('module');
const { JSDOM } = require('jsdom');

const root = join(__dirname, '..');
const scratch = process.env.SCRATCH_DIR || join(root, '..', 'scratch');
const logPath = join(scratch, 'frontend-controller.log');
const lines = [];
const log = (m) => { lines.push(m); console.log(m); };

const origResolve = Module._resolveFilename;
Module._resolveFilename = function (request, parent, isMain, options) {
  if (request === 'lightweight-charts') {
    return join(__dirname, 'mock-lightweight-charts.cjs');
  }
  return origResolve.call(this, request, parent, isMain, options);
};

require('tsx/cjs');

const dom = new JSDOM(
  '<!DOCTYPE html><html><body><div id="chart" style="width:640px;height:420px"></div></body></html>',
  { url: 'http://127.0.0.1:3000/' },
);
global.window = dom.window;
global.document = dom.window.document;
global.HTMLElement = dom.window.HTMLElement;
global.NodeJS = { Timeout: class {} };
global.requestAnimationFrame = (cb) => setTimeout(() => cb(0), 0);

const panelFiles = [
  'src/app/page.tsx',
  'src/hooks/useReplayController.ts',
  'src/components/ArenaLobby.tsx',
  'src/components/ChartView.tsx',
  'src/components/ResourceBars.tsx',
  'src/components/SaboPanel.tsx',
];

for (const f of panelFiles) {
  const src = readFileSync(join(root, f), 'utf8');
  if (/\brequire\s*\(/.test(src) || /\bmodule\.exports\b/.test(src)) {
    throw new Error(`${f} exposes Node globals`);
  }
  log(`OK static ${f}`);
}

const pageSrc = readFileSync(join(root, 'src/app/page.tsx'), 'utf8');
if (!pageSrc.includes("sendWSAction('submit_order'")) {
  throw new Error('page.tsx must send submit_order via WS');
}
log('OK page.tsx wires submit_order to sendWSAction');

const React = require('react');
const { renderHook, act } = require('@testing-library/react');
const { useReplayController } = require('../src/hooks/useReplayController.ts');
const { SAMPLE_ARENAS } = require('../src/lib/sampleArenas.ts');

const container = document.getElementById('chart');
const containerRef = { current: container };
const bars = SAMPLE_ARENAS[0].bars;

const { result } = renderHook(() => useReplayController({ containerRef, initialBars: bars }), {
  wrapper: ({ children }) => React.createElement(React.Fragment, null, children),
});

log(`initial index=${result.current.currentIndex}`);
act(() => result.current.seekTo(4));
log(`seekTo(4) index=${result.current.currentIndex}`);
act(() => result.current.addPlayerMarker(4, true, 'p1'));
act(() => result.current.updateFromServer(6, bars[6]));
log(`updateFromServer(6) index=${result.current.currentIndex}`);
act(() => result.current.play());
log(`play isPlaying=${result.current.isPlaying}`);

if (result.current.currentIndex < 4) throw new Error('currentIndex did not advance');
log('PASS controller state transitions');

mkdirSync(scratch, { recursive: true });
writeFileSync(logPath, lines.join('\n') + '\n');
log(`wrote ${logPath}`);