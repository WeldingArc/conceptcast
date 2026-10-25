// Test a built ConceptCast app in Safari's engine (WebKit), silently. macOS only.
//
//   swift scripts/webkit_test.swift path/to/app.html [screenshot_dir]
//
// Checks: page loads without JS errors · every beat of every concept renders (exactly one active
// diagram with a highlighted item; recap beats show the recap; no sideways overflow) · narrated
// playback advances on its own (recorded clips if embedded, else the built-in voice) · ←/→ move
// exactly one beat · pause stops audio · voice-off playback advances on the reading timer · the
// first chapter's recall quiz grades every correct answer as correct · results are saved and the
// home screen shows them. Prints one JSON line per check and exits 1 if any check fails.
// Audio is muted (media volume ~0, speech stubbed) so nothing plays out loud.
// Note: a hidden window throttles timers and pauses CSS transitions, so timings here are slow;
// screenshots are taken with transitions disabled.
import Cocoa
import WebKit

let htmlPath = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ""
let shotDir = CommandLine.arguments.count > 2 ? CommandLine.arguments[2] : ""
if htmlPath.isEmpty { print("usage: swift webkit_test.swift app.html [screenshot_dir]"); exit(2) }
let fileURL = URL(fileURLWithPath: htmlPath)

final class Harness: NSObject, WKNavigationDelegate {
    var web: WKWebView!
    var window: NSWindow!
    var steps: [(String, (@escaping () -> Void) -> Void)] = []
    var failed = 0

    func start() {
        let cfg = WKWebViewConfiguration()
        let uc = WKUserContentController()
        let boot = """
        window.__errs = []; window.__ev = []; window.__t0 = performance.now();
        window.addEventListener('error', function (e) { window.__errs.push(String(e.message) + ' @' + e.lineno); });
        (function () {
          var P0 = HTMLMediaElement.prototype.play;
          HTMLMediaElement.prototype.play = function () {
            this.volume = 0.0001;
            if (!this.__hooked) { this.__hooked = true; var el = this;
              ['play', 'ended'].forEach(function (k) { el.addEventListener(k, function () {
                window.__ev.push({ t: Math.round(performance.now() - window.__t0), k: k, b: window.__player ? window.__player.state().b : -1 }); }); }); }
            return P0.call(this);
          };
          if (window.speechSynthesis) {
            speechSynthesis.speak = function (u) { window.__ev.push({ t: Math.round(performance.now() - window.__t0), k: 'speak' });
              setTimeout(function () { u.onend && u.onend({}); }, 300); };
          }
        })();
        """
        uc.addUserScript(WKUserScript(source: boot, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        cfg.userContentController = uc
        cfg.mediaTypesRequiringUserActionForPlayback = []
        web = WKWebView(frame: NSRect(x: 0, y: 0, width: 1280, height: 820), configuration: cfg)
        web.navigationDelegate = self
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1280, height: 820), styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = web
        window.setFrameOrigin(NSPoint(x: -4000, y: -4000))
        window.orderBack(nil)
        web.loadFileURL(fileURL, allowingReadAccessTo: fileURL.deletingLastPathComponent())
    }

    func webView(_ w: WKWebView, didFinish n: WKNavigation!) { runNext() }

    // body must return JSON with an "ok" boolean
    func check(_ name: String, _ body: String) {
        steps.append((name, { done in
            self.web.callAsyncJavaScript(body, arguments: [:], in: nil, in: .page) { r in
                var line = ""
                switch r {
                case .success(let v): line = "\(v ?? "")"
                case .failure(let e): line = "{\"ok\":false,\"error\":\"\(e)\"}"
                }
                if !line.contains("\"ok\":true") { self.failed += 1 }
                print("\(line.contains("\"ok\":true") ? "PASS" : "FAIL") \(name): \(line)")
                done()
            }
        }))
    }

    func snap(_ name: String, _ setup: String) {
        if shotDir.isEmpty { return }
        steps.append((name, { done in
            let js = "document.getElementById('__notrans') || document.head.insertAdjacentHTML('beforeend', '<style id=\\\"__notrans\\\">*,*::before,*::after{transition:none!important;animation:none!important}</style>'); " + setup + "; return 'ok';"
            self.web.callAsyncJavaScript(js, arguments: [:], in: nil, in: .page) { _ in
                self.web.takeSnapshot(with: WKSnapshotConfiguration()) { img, _ in
                    if let img = img, let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
                       let png = rep.representation(using: .png, properties: [:]) {
                        try? png.write(to: URL(fileURLWithPath: shotDir + "/" + name + ".png"))
                        print("SHOT \(shotDir)/\(name).png")
                    }
                    done()
                }
            }
        }))
    }

    func runNext() {
        if steps.isEmpty { print(failed == 0 ? "ALL PASSED" : "\(failed) CHECK(S) FAILED"); exit(failed == 0 ? 0 : 1) }
        let (_, f) = steps.removeFirst()
        f { DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { self.runNext() } }
    }
}

let h = Harness()
let pre = """
const sleep = ms => new Promise(r => setTimeout(r, ms));
const src = [...document.scripts].map(s => s.textContent).find(t => t.includes('var DATA = '));
const D = JSON.parse(src.slice(src.indexOf('var DATA = ') + 11, src.indexOf(';\\n  var CH = DATA')));
const tx = x => { const d = document.createElement('div'); d.innerHTML = x; return d.textContent.trim(); };
const P = window.__player;

"""

h.check("load", pre + """
await sleep(1500);
try { localStorage.removeItem('conceptcast-' + D.id + '-v1'); } catch (e) {}
const nav = performance.getEntriesByType('navigation')[0];
const v = P.voice();
return JSON.stringify({ ok: window.__errs.length === 0 && !!document.querySelector('.bigplay'), domReadyMs: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
  chapters: D.chapters.length, concepts: P.cards().length, clips: v.clips, recordedVoice: v.rec, errors: window.__errs });
""")

h.check("every beat renders", pre + """
let total = 0; const bad = [];
for (const id of P.cards()) {
  const card = D.chapters.flatMap(c => c.cards).find(c => c.id === id);
  for (let b = 0; b < card.beats.length; b++) {
    total++;
    const bt = P.jump(id, b);
    const st = document.getElementById('stage');
    if (bt.t === 'vis') {
      const act = st.querySelectorAll('.vis.act');
      if (act.length !== 1) { bad.push(id + '#' + b + ' active diagrams=' + act.length); continue; }
      if (!act[0].querySelector('.now') && !act[0].querySelector('[data-i="f"]')) bad.push(id + '#' + b + ' nothing highlighted');
    } else if (['hook', 'terms', 'ex'].includes(bt.t) && !st.querySelector('.recap.act')) bad.push(id + '#' + b + ' recap missing');
    if (document.documentElement.scrollWidth > document.documentElement.clientWidth) bad.push(id + '#' + b + ' horizontal overflow');
  }
}
return JSON.stringify({ ok: bad.length === 0 && window.__errs.length === 0, beats: total, problems: bad.slice(0, 20), errors: window.__errs });
""")

h.check("narrated playback, skip, pause", pre + """
window.__ev.length = 0;
const first = P.cards()[0];
P.jump(first, 0);
document.getElementById('pl-play').click();
await sleep(9000);
const advanced = P.state().b;
const before = P.state();
document.querySelector('[data-act="next"]').click(); await sleep(150);
const afterNext = P.state();
document.querySelector('[data-act="prev"]').click(); await sleep(150);
const afterPrev = P.state();
document.getElementById('pl-play').click(); await sleep(400);
const paused = P.state().playing === false && !P.voice().playing;
const sameCard = (a, b) => a.ci === b.ci && a.ch === b.ch;
const oneStep = (sameCard(before, afterNext) ? afterNext.b === before.b + 1 : afterNext.b === 0) && (afterPrev.b === before.b || !sameCard(before, afterNext));
return JSON.stringify({ ok: advanced >= 2 && oneStep && paused, beatsAdvancedIn9s: advanced, skip: [before.b, afterNext.b, afterPrev.b], paused,
  audioEvents: window.__ev.slice(0, 12).map(e => e.k + '@' + e.t).join(' ') });
""")

h.check("voice-off playback", pre + """
const first = P.cards()[0];
P.jump(first, 0);
const vb = document.getElementById('pl-voice');
const turnedOff = vb.getAttribute('aria-label') === D.ui.voiceOffAria;
if (turnedOff) vb.click();
document.getElementById('pl-play').click();
await sleep(8000);
const b = P.state().b;
document.getElementById('pl-play').click();
if (turnedOff) vb.click();
return JSON.stringify({ ok: b >= 1, beatAfter8s: b });
""")

h.check("chapter 1 recall quiz", pre + """
document.querySelector('[data-act="home"]') && document.querySelector('[data-act="home"]').click(); await sleep(300);
const ch = D.chapters[0];
const btn = document.querySelector('[data-act="quiz"][data-ch="0"]');
btn.click(); await sleep(500);
const log = [];
for (let n = 0; n < 60; n++) {
  const qq = document.querySelector('.qq'); if (!qq) break;
  const hit = Object.entries(D.bank).find(([k, v]) => tx(v.q) === qq.textContent.trim());
  if (!hit) { log.push('question not found'); break; }
  const [qid, q] = hit;
  const right = [...document.querySelectorAll('.opt')].find(b => q.type === 'ox' ? b.dataset.v === q.a : +b.dataset.v === q.a);
  await sleep(400); right.click(); await sleep(200);
  const fb = document.querySelector('.fb');
  log.push(qid + (fb && fb.classList.contains('ok') ? ':ok' : ':WRONG'));
  document.querySelector('.qnext').click(); await sleep(300);
}
const expected = ch.cards.filter(c => c.qids.length).length;
const ring = document.querySelector('.ring .rt');
return JSON.stringify({ ok: log.length === expected && log.every(x => x.endsWith(':ok')) && !!ring, answered: log.length, expected, result: ring && ring.textContent, errors: window.__errs });
""")

h.check("results saved, home shows them", pre + """
document.querySelector('[data-act="home"]').click(); await sleep(500);
let saved = null; try { saved = JSON.parse(localStorage.getItem('conceptcast-' + D.id + '-v1')).score; } catch (e) {}
const stat = document.querySelector('.chc-stat') && document.querySelector('.chc-stat').textContent;
try { localStorage.removeItem('conceptcast-' + D.id + '-v1'); } catch (e) {}
return JSON.stringify({ ok: !!saved && Object.keys(saved).length === 1 && P.state().view === 'home', saved, chapterCard: stat, errors: window.__errs });
""")

h.snap("1-home", "window.__player && document.querySelector('[data-act=\"home\"]') && document.querySelector('[data-act=\"home\"]').click()")
h.snap("2-first-diagram", "const P = window.__player; const id = P.cards()[0]; const src = [...document.scripts].map(s => s.textContent).find(t => t.includes('var DATA = ')); const D = JSON.parse(src.slice(src.indexOf('var DATA = ') + 11, src.indexOf(';\\n  var CH = DATA'))); const c = D.chapters[0].cards[0]; const last = c.beats.map((b, i) => [b, i]).filter(x => x[0].t === 'vis').pop(); P.jump(id, last ? last[1] : 1)")

DispatchQueue.main.asyncAfter(deadline: .now() + 600) { print("TIMEOUT"); exit(3) }
let app = NSApplication.shared
app.setActivationPolicy(.prohibited)
h.start()
app.run()
