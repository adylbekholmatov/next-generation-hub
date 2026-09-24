/* Next-Generation-Hub — немного чистого JS. Сайт работает и без него. */
(function () {
  "use strict";
  var doc = document.documentElement;
  doc.classList.remove("no-js");

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  /* --- Тема ------------------------------------------------------------- */
  var THEME_KEY = "ngh-theme";
  function storeTheme(value) { try { localStorage.setItem(THEME_KEY, value); } catch (e) { /* приватный режим */ } }
  function applyTheme(theme) {
    doc.setAttribute("data-theme", theme);
    $$("[data-theme-toggle]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    });
    var meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#0a0a0a" : "#ffffff");
  }
  applyTheme(doc.getAttribute("data-theme") || "light");
  $$("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = doc.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(next);
      storeTheme(next);
    });
  });
  // Если пользователь не выбирал тему явно — следуем системе.
  if (window.matchMedia) {
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    var onChange = function (e) {
      var saved = null;
      try { saved = localStorage.getItem(THEME_KEY); } catch (err) { saved = null; }
      if (!saved) applyTheme(e.matches ? "dark" : "light");
    };
    if (mq.addEventListener) mq.addEventListener("change", onChange);
  }

  /* --- Шапка и мобильное меню ------------------------------------------ */
  var header = $(".site-header");
  if (header) {
    var onScroll = function () { header.classList.toggle("is-scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }
  var mobileNav = $("#mobile-nav");
  function setMobileNav(open) {
    if (!mobileNav) return;
    mobileNav.classList.toggle("is-open", open);
    mobileNav.setAttribute("aria-hidden", open ? "false" : "true");
    $$("[data-mobile-nav-open]").forEach(function (b) { b.setAttribute("aria-expanded", open ? "true" : "false"); });
    document.body.style.overflow = open ? "hidden" : "";
    if (open) { var first = $("a, button", mobileNav); if (first) first.focus(); }
  }
  $$("[data-mobile-nav-open]").forEach(function (b) { b.addEventListener("click", function () { setMobileNav(true); }); });
  $$("[data-mobile-nav-close]").forEach(function (b) { b.addEventListener("click", function () { setMobileNav(false); }); });
  if (mobileNav) $$("nav a", mobileNav).forEach(function (a) { a.addEventListener("click", function () { setMobileNav(false); }); });

  /* --- Боковое меню кабинета ------------------------------------------- */
  var cab = $(".cab");
  function setCabNav(open) {
    if (!cab) return;
    cab.classList.toggle("is-nav-open", open);
    $$("[data-cab-nav-toggle]").forEach(function (b) { b.setAttribute("aria-expanded", open ? "true" : "false"); });
  }
  $$("[data-cab-nav-toggle]").forEach(function (b) {
    b.addEventListener("click", function () { setCabNav(!cab.classList.contains("is-nav-open")); });
  });
  $$("[data-cab-nav-close]").forEach(function (b) { b.addEventListener("click", function () { setCabNav(false); }); });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { setMobileNav(false); setCabNav(false); }
  });

  /* --- Flash-сообщения -------------------------------------------------- */
  function dismiss(msg) {
    msg.classList.add("is-leaving");
    setTimeout(function () { if (msg.parentNode) msg.parentNode.removeChild(msg); }, 300);
  }
  $$(".message").forEach(function (msg, i) {
    var btn = $("button", msg);
    if (btn) btn.addEventListener("click", function () { dismiss(msg); });
    // Сообщения с паролями не прячем автоматически.
    if (!msg.hasAttribute("data-sticky")) setTimeout(function () { dismiss(msg); }, 6000 + i * 800);
  });

  /* --- Подтверждение опасных действий ---------------------------------- */
  document.addEventListener("submit", function (e) {
    var form = e.target;
    var text = form.getAttribute("data-confirm");
    if (text && !window.confirm(text)) e.preventDefault();
  }, true);

  /* --- Появление при прокрутке ----------------------------------------- */
  var reveals = $$(".reveal");
  if ("IntersectionObserver" in window && reveals.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add("is-visible"); io.unobserve(entry.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("is-visible"); });
  }

  /* --- Языковые вкладки в формах --------------------------------------- */
  $$("[data-lang-tabs]").forEach(function (box) {
    var tabs = $$("[role=tab]", box);
    var panes = $$("[role=tabpanel]", box);
    function select(tab) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
      });
      panes.forEach(function (p) { p.hidden = p.id !== tab.getAttribute("aria-controls"); });
    }
    function refreshDots() {
      tabs.forEach(function (t) {
        var pane = document.getElementById(t.getAttribute("aria-controls"));
        var dot = $(".dot", t);
        if (!pane || !dot || dot.classList.contains("is-error")) return;
        var filled = $$("input, textarea", pane).some(function (f) { return f.value.trim() !== ""; });
        dot.classList.toggle("is-filled", filled);
      });
    }
    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function () { select(tab); });
      tab.addEventListener("keydown", function (e) {
        var dir = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
        if (!dir) return;
        var next = tabs[(i + dir + tabs.length) % tabs.length];
        next.focus(); select(next);
      });
    });
    box.addEventListener("input", refreshDots);
    refreshDots();
    var withError = tabs.filter(function (t) { return $(".dot.is-error", t); })[0];
    if (withError) select(withError);
  });

  /* --- Фильтр в длинных чекбокс-списках -------------------------------- */
  $$("[data-filter-list]").forEach(function (input) {
    var list = document.getElementById(input.getAttribute("data-filter-list"));
    if (!list) return;
    var counter = input.getAttribute("data-counter") ? document.getElementById(input.getAttribute("data-counter")) : null;
    function count() {
      if (counter) counter.textContent = $$("input:checked", list).length;
    }
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      $$("label", list).forEach(function (label) {
        label.classList.toggle("is-hidden", q && label.textContent.toLowerCase().indexOf(q) === -1);
      });
    });
    list.addEventListener("change", count);
    count();
  });

  /* --- Журнал: «Все присутствуют» и счётчики --------------------------- */
  var markForm = $("[data-mark-form]");
  if (markForm) {
    var summary = function () {
      var counts = { present: 0, late: 0, absent: 0, excused: 0, none: 0 };
      $$("tbody tr[data-student]", markForm).forEach(function (row) {
        var checked = $("input[type=radio]:checked", row);
        counts[checked ? checked.value : "none"] += 1;
        row.classList.toggle("is-unmarked", !checked);
        var grade = $("input.grade", row);
        if (grade) {
          var off = checked && (checked.value === "absent" || checked.value === "excused");
          grade.disabled = !!off;
          if (off) grade.value = "";
        }
      });
      Object.keys(counts).forEach(function (k) {
        var el = $('[data-count="' + k + '"]', markForm);
        if (el) el.textContent = counts[k];
      });
    };
    markForm.addEventListener("change", summary);
    $$("[data-all-present]", markForm).forEach(function (btn) {
      btn.addEventListener("click", function () {
        $$('input[type=radio][value="present"]', markForm).forEach(function (r) { r.checked = true; });
        summary();
      });
    });
    summary();
  }

  /* --- Загрузка файла с прогрессом ------------------------------------- */
  $$(".dropzone").forEach(function (zone) {
    var input = $("input[type=file]", zone);
    var name = $(".file-name", zone);
    if (!input) return;
    input.addEventListener("change", function () {
      if (name) {
        var f = input.files && input.files[0];
        name.textContent = f ? f.name + " · " + (f.size / 1048576).toFixed(1) + " MB" : "";
      }
    });
    ["dragenter", "dragover"].forEach(function (ev) { zone.addEventListener(ev, function () { zone.classList.add("is-drag"); }); });
    ["dragleave", "drop"].forEach(function (ev) { zone.addEventListener(ev, function () { zone.classList.remove("is-drag"); }); });
  });

  $$("form[data-upload]").forEach(function (form) {
    var progress = $(".progress", form);
    var bar = progress ? $(".progress-bar span", progress) : null;
    var pct = progress ? $("[data-progress-pct]", progress) : null;
    var info = progress ? $("[data-progress-info]", progress) : null;
    var submit = $("[type=submit]", form);
    var maxMb = parseFloat(form.getAttribute("data-max-mb") || "0");

    function clearErrors() {
      $$(".js-error", form).forEach(function (el) { el.parentNode.removeChild(el); });
      $$(".field.has-error", form).forEach(function (el) { el.classList.remove("has-error"); });
    }
    function showErrors(errors) {
      Object.keys(errors).forEach(function (field) {
        var target = field === "__all__" ? $("[data-form-errors]", form) : $('[data-field="' + field + '"]', form);
        if (!target) target = $("[data-form-errors]", form);
        var ul = document.createElement("ul");
        ul.className = "errors js-error";
        errors[field].forEach(function (msg) {
          var li = document.createElement("li"); li.textContent = msg; ul.appendChild(li);
        });
        if (field === "__all__" || !target.classList.contains("field")) {
          ul.className = "alert alert-bad js-error"; ul.style.listStyle = "none";
          target.appendChild(ul);
        } else {
          target.classList.add("has-error"); target.appendChild(ul);
        }
      });
      var first = $(".js-error", form);
      if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    form.addEventListener("submit", function (e) {
      if (!window.FormData || !window.XMLHttpRequest) return;
      var fileInput = $('input[type=file][name="video_file"]', form);
      var file = fileInput && fileInput.files && fileInput.files[0];
      if (file && maxMb && file.size > maxMb * 1048576) {
        e.preventDefault();
        clearErrors();
        var err = {}; err.video_file = [form.getAttribute("data-size-error")];
        showErrors(err);
        return;
      }
      e.preventDefault();
      clearErrors();
      var xhr = new XMLHttpRequest();
      xhr.open("POST", form.action || window.location.href);
      xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
      if (progress) progress.classList.add("is-visible");
      if (submit) submit.disabled = true;
      var started = Date.now();
      xhr.upload.addEventListener("progress", function (ev) {
        if (!ev.lengthComputable || !bar) return;
        var p = Math.round(ev.loaded * 100 / ev.total);
        bar.style.width = p + "%";
        if (pct) pct.textContent = p + "%";
        if (info) {
          var secs = (Date.now() - started) / 1000;
          var speed = secs > 0 ? ev.loaded / secs / 1048576 : 0;
          info.textContent = (ev.loaded / 1048576).toFixed(1) + " / " + (ev.total / 1048576).toFixed(1) + " MB · " + speed.toFixed(1) + " MB/s";
        }
      });
      xhr.onload = function () {
        var data = null;
        try { data = JSON.parse(xhr.responseText); } catch (err) { data = null; }
        if (data && data.ok && data.redirect) { window.location.href = data.redirect; return; }
        if (submit) submit.disabled = false;
        if (progress) progress.classList.remove("is-visible");
        if (bar) bar.style.width = "0";
        if (data && data.errors) { showErrors(data.errors); return; }
        showErrors({ __all__: [form.getAttribute("data-generic-error")] });
      };
      xhr.onerror = function () {
        if (submit) submit.disabled = false;
        if (progress) progress.classList.remove("is-visible");
        showErrors({ __all__: [form.getAttribute("data-network-error")] });
      };
      xhr.send(new FormData(form));
    });
  });

  /* --- Автоотправка фильтров ------------------------------------------- */
  $$("[data-autosubmit]").forEach(function (el) {
    el.addEventListener("change", function () { if (el.form) el.form.submit(); });
  });

  /* --- Копирование в буфер --------------------------------------------- */
  $$("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy");
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(function () {
        var old = btn.getAttribute("aria-label");
        btn.setAttribute("aria-label", btn.getAttribute("data-copied") || "OK");
        btn.classList.add("is-copied");
        setTimeout(function () { btn.classList.remove("is-copied"); btn.setAttribute("aria-label", old || ""); }, 1500);
      });
    });
  });
})();
