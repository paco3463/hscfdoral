/* Healthy Solutions for Children and Families — site interactions
   Plain JavaScript, no dependencies. Each feature checks that its markup exists. */
(function () {
  "use strict";

  var doc = document;
  var root = doc.documentElement;
  var lang = root.lang && root.lang.indexOf("es") === 0 ? "es" : "en";
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var store = {
    get: function (k, s) { try { return (s ? sessionStorage : localStorage).getItem(k); } catch (e) { return null; } },
    set: function (k, v, s) { try { (s ? sessionStorage : localStorage).setItem(k, v); } catch (e) {} }
  };
  function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }

  /* ---------- footer year ---------- */
  $$("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });

  /* ---------- header shadow on scroll ---------- */
  var header = $(".site-header");
  if (header) {
    var onScroll = function () { header.classList.toggle("is-scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- services dropdown ---------- */
  $$(".nav-drop").forEach(function (drop) {
    var btn = $("button", drop);
    var closeTimer;
    function open(v) {
      drop.classList.toggle("is-open", v);
      btn.setAttribute("aria-expanded", v ? "true" : "false");
    }
    btn.addEventListener("click", function () { open(!drop.classList.contains("is-open")); });
    drop.addEventListener("mouseenter", function () { clearTimeout(closeTimer); if (window.matchMedia("(hover: hover)").matches) open(true); });
    drop.addEventListener("mouseleave", function () { closeTimer = setTimeout(function () { open(false); }, 180); });
    drop.addEventListener("focusout", function (e) { if (!drop.contains(e.relatedTarget)) open(false); });
    doc.addEventListener("keydown", function (e) { if (e.key === "Escape" && drop.classList.contains("is-open")) { open(false); btn.focus(); } });
    doc.addEventListener("click", function (e) { if (!drop.contains(e.target)) open(false); });
  });

  /* ---------- mobile menu ---------- */
  var sheet = $(".mobile-sheet");
  var toggle = $(".menu-toggle");
  if (sheet && toggle) {
    var closeBtn = $(".mobile-close", sheet);
    var setSheet = function (v) {
      sheet.classList.toggle("is-open", v);
      sheet.setAttribute("aria-hidden", v ? "false" : "true");
      toggle.setAttribute("aria-expanded", v ? "true" : "false");
      doc.body.classList.toggle("is-locked", v);
      if (v) { sheet.removeAttribute("inert"); closeBtn.focus(); } else { sheet.setAttribute("inert", ""); toggle.focus(); }
    };
    toggle.addEventListener("click", function () { setSheet(true); });
    closeBtn.addEventListener("click", function () { setSheet(false); });
    doc.addEventListener("keydown", function (e) { if (e.key === "Escape" && sheet.classList.contains("is-open")) setSheet(false); });
  }

  /* ---------- splash screen (homepage only, once per visit) ---------- */
  var splash = $(".splash");
  var afterEnter = [];
  function whenEntered(fn) { if (!splash || splash.hasAttribute("hidden")) fn(); else afterEnter.push(fn); }
  if (splash) {
    var skip = store.get("hscf_entered", true) === "1" || /[?&]nosplash/.test(location.search);
    if (skip) {
      splash.setAttribute("hidden", "");
    } else {
      doc.body.classList.add("is-locked");
      var door = $(".splash-door", splash);
      var entered = false;
      var enter = function () {
        if (entered) return; entered = true;
        store.set("hscf_entered", "1", true);
        splash.classList.add("is-entering");
        var t1 = reduceMotion ? 50 : 900;
        setTimeout(function () {
          doc.body.classList.add("site-reveal");
          splash.classList.add("is-leaving");
          doc.body.classList.remove("is-locked");
        }, t1);
        setTimeout(function () {
          splash.setAttribute("hidden", "");
          afterEnter.forEach(function (fn) { fn(); });
          afterEnter = [];
          var h1 = $("main h1");
          if (h1) { h1.setAttribute("tabindex", "-1"); h1.focus({ preventScroll: true }); }
        }, t1 + 950);
      };
      door.addEventListener("click", enter);
      splash.addEventListener("keydown", function (e) { if (e.key === "Escape") enter(); });
    }
  }

  /* ---------- hero video: one edited loop with three scenes ---------- */
  var hv = $(".hero-video");
  if (hv) {
    var heroEl = hv.closest(".hero");
    var bars = $$(".scene-bar", heroEl);
    var vtoggle = $(".video-toggle", heroEl);
    var seg = hv.getAttribute("data-segments").split(",").map(Number);
    var paused = reduceMotion;
    var labelPause = vtoggle.getAttribute("data-pause"), labelPlay = vtoggle.getAttribute("data-play");
    var play = function () { var p = hv.play(); if (p && p.catch) p.catch(function () {}); };
    var setPaused = function (p) {
      paused = p;
      vtoggle.setAttribute("aria-pressed", p ? "true" : "false");
      vtoggle.setAttribute("aria-label", p ? labelPlay : labelPause);
      if (p) hv.pause(); else play();
    };
    var draw = function () {
      var t = hv.currentTime || 0;
      bars.forEach(function (b, i) {
        var s0 = seg[i], s1 = seg[i + 1];
        var w = t >= s1 ? 100 : t <= s0 ? 0 : ((t - s0) / (s1 - s0)) * 100;
        $("i", b).style.width = w + "%";
        b.setAttribute("aria-current", t >= s0 && t < s1 ? "true" : "false");
      });
      requestAnimationFrame(draw);
    };
    bars.forEach(function (b, i) { b.addEventListener("click", function () { hv.currentTime = seg[i] + 0.05; if (paused) draw(); }); });
    vtoggle.addEventListener("click", function () { setPaused(!paused); });
    if (reduceMotion) { hv.removeAttribute("autoplay"); hv.pause(); }
    // Start from the first scene when the visitor walks through the splash door
    whenEntered(function () { try { hv.currentTime = 0; } catch (e) {} setPaused(paused); requestAnimationFrame(draw); });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (!paused) { if (en.isIntersecting) play(); else hv.pause(); } });
      }, { threshold: 0.05 }).observe(heroEl);
    }
  }

  /* ---------- path finder ---------- */
  var finder = $("[data-finder]");
  if (finder && window.HSCF_FINDER) {
    var data = window.HSCF_FINDER;
    var whoGrid = $(".who-grid", finder);
    var step2 = $(".finder-step", finder);
    var concernList = $(".concern-list", finder);
    var result = $(".finder-result", finder);
    var arrow = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 5l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    var current = null;

    $$(".who", whoGrid).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-who");
        current = data.groups.filter(function (g) { return g.id === id; })[0];
        $$(".who", whoGrid).forEach(function (b) { b.setAttribute("aria-pressed", b === btn ? "true" : "false"); });
        whoGrid.classList.add("has-choice");
        concernList.innerHTML = "";
        current.concerns.forEach(function (c, i) {
          var cb = doc.createElement("button");
          cb.type = "button"; cb.className = "concern"; cb.setAttribute("aria-pressed", "false");
          cb.textContent = c[0];
          cb.addEventListener("click", function () { pick(i, cb); });
          concernList.appendChild(cb);
        });
        result.hidden = true;
        step2.hidden = false;
        var first = $(".concern", concernList);
        if (first) first.focus({ preventScroll: true });
        step2.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest" });
      });
    });

    function pick(i, cbtn) {
      $$(".concern", concernList).forEach(function (b) { b.setAttribute("aria-pressed", b === cbtn ? "true" : "false"); });
      var c = current.concerns[i];
      var list = $(".rec-list", result);
      list.innerHTML = c[1].map(function (sid) {
        var s = data.services[sid];
        return '<li><a href="' + s.url + '"><span>' + s.name + "</span>" + arrow + "</a></li>";
      }).join("");
      var p = data.people[c[2]];
      var m = $(".match", result);
      m.innerHTML =
        '<div class="house-img house"><img src="' + p.img + '" alt="" loading="lazy"></div>' +
        "<div><p>" + data.labels.match + "</p><strong>" + p.name + "</strong>" +
        '<div class="role">' + p.role + "</div>" +
        '<a class="text-link" href="' + p.url + '">' + data.labels.meet + " " + p.first + "</a></div>";
      result.hidden = false;
      result.classList.remove("is-in"); void result.offsetWidth; result.classList.add("is-in");
      result.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest" });
    }
    var restart = $(".finder-restart", finder);
    if (restart) restart.addEventListener("click", function () {
      $$(".who", whoGrid).forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
      whoGrid.classList.remove("has-choice");
      step2.hidden = true; result.hidden = true;
      $(".who", whoGrid).focus();
    });
  }

  /* ---------- one calm minute (breathing) ---------- */
  var breathe = $("[data-breathe]");
  if (breathe) {
    var stage = $(".breathe-stage", breathe);
    var label = $(".breathe-label", breathe);
    var count = $(".breathe-count", breathe);
    var bbtn = $(".breathe-btn", breathe);
    var L = JSON.parse(breathe.getAttribute("data-labels"));
    var phases = [["in", 4], ["hold", 4], ["out", 6]];
    var running = false, timers = [], cycle = 0, CYCLES = 4;
    var clear = function () { timers.forEach(clearTimeout); timers = []; };
    var setPhase = function (name) {
      stage.classList.remove("is-in", "is-hold", "is-out");
      if (name) stage.classList.add("is-" + name);
    };
    var countdown = function (secs) {
      for (var s = 0; s < secs; s++) {
        (function (n) { timers.push(setTimeout(function () { count.textContent = String(secs - n); }, n * 1000)); })(s);
      }
    };
    var run = function () {
      var t = 0;
      phases.forEach(function (ph) {
        timers.push(setTimeout(function () { setPhase(ph[0]); label.textContent = L[ph[0]]; countdown(ph[1]); }, t * 1000));
        t += ph[1];
      });
      timers.push(setTimeout(function () {
        cycle++;
        if (cycle < CYCLES && running) run(); else stop(true);
      }, t * 1000));
    };
    var stop = function (done) {
      running = false; clear(); setPhase(null);
      label.textContent = done ? L.done : L.ready; count.textContent = "";
      bbtn.textContent = L.start; bbtn.setAttribute("aria-pressed", "false");
    };
    bbtn.addEventListener("click", function () {
      if (running) { stop(false); return; }
      running = true; cycle = 0;
      bbtn.textContent = L.stop; bbtn.setAttribute("aria-pressed", "true");
      run();
    });
  }

  /* ---------- filters (staff page and blog) ---------- */
  var filters = $("[data-filters]");
  if (filters) {
    var cards = $$(filters.getAttribute("data-filters") || ".team-card");
    var empty = $(".team-empty");
    $$(".chip", filters).forEach(function (chip) {
      chip.addEventListener("click", function () {
        var f = chip.getAttribute("data-filter");
        $$(".chip", filters).forEach(function (c) { c.setAttribute("aria-pressed", c === chip ? "true" : "false"); });
        var shown = 0;
        cards.forEach(function (card) {
          var match = f === "all" || (" " + card.getAttribute("data-tags") + " ").indexOf(" " + f + " ") > -1;
          card.hidden = !match; if (match) shown++;
        });
        if (empty) empty.hidden = shown > 0;
      });
    });
  }

  /* ---------- videos: load YouTube only after a click (privacy and speed) ---------- */
  $$("[data-yt]").forEach(function (box) {
    var link = $(".yt-link", box);
    link.addEventListener("click", function (e) {
      e.preventDefault();
      var f = doc.createElement("iframe");
      f.src = "https://www.youtube-nocookie.com/embed/" + box.getAttribute("data-yt") + "?autoplay=1&rel=0";
      f.title = link.getAttribute("aria-label") || "YouTube";
      f.allow = "accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture";
      f.allowFullscreen = true;
      link.replaceWith(f);
      f.focus();
    });
  });

  /* ---------- gallery lightbox ---------- */
  $$("[data-gallery]").forEach(function (gal) {
    var items = $$(".g-item", gal);
    if (!items.length || typeof HTMLDialogElement === "undefined") return;
    var labels = JSON.parse(gal.getAttribute("data-labels") || "{}");
    var chev = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M7 4l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    var x = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
    var box = doc.createElement("dialog");
    box.className = "lightbox";
    box.innerHTML = '<figure><img alt=""><p></p></figure>' +
      '<button class="lb-btn lb-close" type="button" aria-label="' + (labels.close || "Close") + '">' + x + "</button>" +
      '<button class="lb-btn lb-prev" type="button" aria-label="' + (labels.prev || "Previous") + '">' + chev + "</button>" +
      '<button class="lb-btn lb-next" type="button" aria-label="' + (labels.next || "Next") + '">' + chev + "</button>";
    doc.body.appendChild(box);
    var img = $("img", box), cap = $("p", box), idx = 0;
    var show = function (i) {
      idx = (i + items.length) % items.length;
      var it = items[idx], thumb = $("img", it);
      img.src = it.getAttribute("href"); img.alt = thumb.alt; cap.textContent = thumb.alt;
    };
    items.forEach(function (it, i) {
      it.addEventListener("click", function (e) { e.preventDefault(); show(i); box.showModal(); });
    });
    $(".lb-close", box).addEventListener("click", function () { box.close(); });
    $(".lb-prev", box).addEventListener("click", function () { show(idx - 1); });
    $(".lb-next", box).addEventListener("click", function () { show(idx + 1); });
    box.addEventListener("click", function (e) { if (e.target === box) box.close(); });
    box.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") show(idx + 1);
      if (e.key === "ArrowLeft") show(idx - 1);
    });
    box.addEventListener("close", function () { if (items[idx]) items[idx].focus(); });
  });

  /* ---------- event popup ---------- */
  var modal = $("#event-modal");
  var pill = $(".event-pill");
  if (modal) {
    var endAt = new Date(modal.getAttribute("data-end")).getTime();
    var KEY = "hscf_event_" + modal.getAttribute("data-id");
    if (Date.now() > endAt) {
      modal.remove(); if (pill) pill.remove();
    } else {
      var openModal = function () {
        if (typeof modal.showModal === "function") { if (!modal.open) modal.showModal(); }
        else modal.setAttribute("open", "");
        if (pill) pill.classList.remove("is-shown");
      };
      var closeModal = function () {
        store.set(KEY, "seen");
        if (reduceMotion || typeof modal.close !== "function") { if (modal.close) modal.close(); else modal.removeAttribute("open"); afterClose(); return; }
        modal.classList.add("is-closing");
        setTimeout(function () { modal.classList.remove("is-closing"); modal.close(); afterClose(); }, 340);
      };
      var afterClose = function () { if (pill) setTimeout(function () { pill.classList.add("is-shown"); }, 400); };
      $$("[data-close]", modal).forEach(function (b) { b.addEventListener("click", closeModal); });
      modal.addEventListener("cancel", function (e) { e.preventDefault(); closeModal(); });
      modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });
      if (pill) pill.addEventListener("click", openModal);
      $$("[data-open-event]").forEach(function (b) { b.addEventListener("click", function (e) { e.preventDefault(); openModal(); }); });

      // Add to calendar (.ics download)
      var ics = $("[data-ics]", modal);
      if (ics) ics.addEventListener("click", function () {
        var d = JSON.parse(ics.getAttribute("data-ics"));
        var body = [
          "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//HSCF//Event//" + lang.toUpperCase(), "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
          "BEGIN:VEVENT",
          "UID:" + d.uid,
          "DTSTAMP:" + new Date().toISOString().replace(/[-:]/g, "").split(".")[0] + "Z",
          "DTSTART:" + d.start, "DTEND:" + d.end,
          "SUMMARY:" + d.title, "LOCATION:" + d.location.replace(/,/g, "\\,"),
          "DESCRIPTION:" + d.description.replace(/,/g, "\\,"),
          "END:VEVENT", "END:VCALENDAR"
        ].join("\r\n");
        var blob = new Blob([body], { type: "text/calendar;charset=utf-8" });
        var a = doc.createElement("a");
        a.href = URL.createObjectURL(blob); a.download = "hablemos-sobre-ansiedad.ics";
        doc.body.appendChild(a); a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
      });

      if (store.get(KEY) === "seen") {
        whenEntered(function () { if (pill) setTimeout(function () { pill.classList.add("is-shown"); }, 1200); });
      } else {
        whenEntered(function () { setTimeout(openModal, splash ? 1800 : 2600); });
      }
    }
  }

  /* ---------- analytics key events (only if the GA4 tag is on the page) ----------
     Sends the action only: never names, emails, phone numbers or what someone wrote. */
  var track = function (name, params) { if (typeof window.gtag === "function") window.gtag("event", name, params || {}); };
  doc.addEventListener("click", function (e) {
    var a = e.target.closest("a, button");
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (href.indexOf("tel:") === 0) track("click_to_call", { link_location: a.closest("header, footer, main, dialog") ? a.closest("header, footer, main, dialog").tagName.toLowerCase() : "page" });
    else if (href.indexOf("mailto:") === 0) track(a.closest("dialog") ? "workshop_rsvp" : "click_email");
    else if (href.indexOf("#book") > -1) track("book_consultation_click");
    else if (a.classList.contains("lang-switch")) track("language_switch", { to: lang === "en" ? "es" : "en" });
    else if (a.classList.contains("who")) track("finder_select", { who: a.getAttribute("data-who") });
  });
  window.HSCF_TRACK = track;

  /* ---------- contact form ---------- */
  var form = $("[data-contact-form]");
  if (form) {
    var status = $(".form-status", form);
    var msgs = JSON.parse(form.getAttribute("data-msgs"));
    var submitBtn = $("button[type=submit]", form);
    var show = function (txt, ok) { status.textContent = txt; status.className = "form-status " + (ok ? "is-ok" : "is-err"); status.hidden = false; status.focus(); };
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if ($(".hp input", form).value) return; // spam trap
      var fd = new FormData(form);
      var name = (fd.get("name") || "").trim(), email = (fd.get("email") || "").trim(), phone = (fd.get("phone") || "").trim();
      if (!name || (!email && !phone)) { show(msgs.required, false); return; }
      var endpoint = form.getAttribute("action");
      if (!endpoint || endpoint.indexOf("YOUR_FORM_ID") > -1) {
        // No form service connected yet: open the visitor's email app with the request filled in.
        var lines = [];
        fd.forEach(function (v, k) { if (k !== "_gotcha" && v) lines.push(k + ": " + v); });
        location.href = "mailto:" + form.getAttribute("data-email") + "?subject=" + encodeURIComponent(msgs.subject) + "&body=" + encodeURIComponent(lines.join("\n"));
        show(msgs.mailto, true);
        track("generate_lead", { method: "email_app" });
        return;
      }
      var original = submitBtn.textContent;
      submitBtn.disabled = true; submitBtn.textContent = msgs.sending;
      fetch(endpoint, { method: "POST", body: fd, headers: { Accept: "application/json" } })
        .then(function (r) { if (!r.ok) throw new Error(r.status); form.reset(); show(msgs.success, true); track("generate_lead", { method: "contact_form" }); })
        .catch(function () { show(msgs.error, false); })
        .then(function () { submitBtn.disabled = false; submitBtn.textContent = original; });
    });
  }
})();
