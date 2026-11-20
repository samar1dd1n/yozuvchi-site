"use strict";

/*
 * Admin panel: bitta sahifali ilova, hamma ma'lumot /api/panel/ orqali.
 * Bo'limlar URL hash bilan: #/muallif, #/kitoblar, #/kitob/5, #/fikrlar, #/fikr/new
 */
(() => {
  const app = document.getElementById("app");
  const toastEl = document.getElementById("toast");
  const state = { user: null };

  const IMAGE_ACCEPT = "image/jpeg,image/png,image/webp";
  const PAGE_ACCEPT = "image/jpeg,image/png,image/webp,application/pdf,.pdf";
  const KINDS = [["news", "Yangilik"], ["article", "Maqola"], ["photo", "Rasm"]];
  const FIELD_LABELS = {
    full_name: "Ism familiya", tagline: "Shior", bio: "Muallif haqida", photo: "Rasm",
    academic_degree: "Ilmiy daraja", science_field: "Ilmiy soha", telegram: "Telegram",
    instagram: "Instagram", email: "Email", title: "Nomi", annotation: "Annotatsiya",
    cover: "Muqova", back_cover: "Orqa muqova", spine_color: "Qirra rangi", order: "Tartib",
    number: "Sahifa raqami", file: "Fayl", files: "Fayllar", publish_at: "Ochilish vaqti",
    start_number: "Boshlang'ich raqam", start_at: "Boshlanish vaqti", interval_days: "Oraliq",
    kind: "Turi", excerpt: "Qisqa tavsif", body: "Matn", image: "Rasm", published_at: "E'lon vaqti",
    username: "Login", password: "Parol", non_field_errors: "",
  };

  // ---------- Yordamchilar ----------
  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const pad = (n) => String(n).padStart(2, "0");
  const later = (a, b) => (a > b ? a : b);
  // Server vaqtni Toshkent vaqtida qaytaradi: "2026-11-12T09:00:00+05:00" -> "2026-11-12T09:00"
  const toInput = (iso) => (iso ? iso.slice(0, 16) : "");
  const fmtDate = (iso) => (iso ? `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}` : "");

  function cookie(name) {
    const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function nowInput() {
    const d = new Date();
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function addDays(input, days) {
    const [date, time] = input.split("T");
    const [y, m, d] = date.split("-").map(Number);
    const dt = new Date(Date.UTC(y, m - 1, d + days));
    return `${dt.getUTCFullYear()}-${pad(dt.getUTCMonth() + 1)}-${pad(dt.getUTCDate())}T${time}`;
  }

  let toastTimer;
  function toast(message, isError = false) {
    toastEl.textContent = message;
    toastEl.classList.toggle("error", isError);
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), isError ? 5000 : 2800);
  }

  // ---------- API ----------
  class ApiError extends Error {
    constructor(status, data) {
      super(`API ${status}`);
      this.status = status;
      this.data = data;
    }
  }

  async function api(path, { method = "GET", json, form } = {}) {
    const headers = { Accept: "application/json" };
    if (method !== "GET") headers["X-CSRFToken"] = cookie("csrftoken");
    let body;
    if (form) {
      body = form;
    } else if (json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(json);
    }
    let res;
    try {
      res = await fetch(`/api${path}`, { method, headers, body, credentials: "same-origin" });
    } catch {
      throw new ApiError(0, null);
    }
    if (res.status === 204) return null;
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (!res.ok) throw new ApiError(res.status, data);
    return data;
  }

  function flatten(value) {
    if (value == null) return [];
    if (Array.isArray(value)) return value.flatMap(flatten);
    if (typeof value === "object") return Object.values(value).flatMap(flatten);
    return [String(value)];
  }

  function errorText(err) {
    if (!(err instanceof ApiError)) return "Kutilmagan xato yuz berdi.";
    if (err.status === 0) return "Server bilan aloqa yo'q. Internetni tekshirib, qayta urinib ko'ring.";
    if (err.status === 413) return "Fayl juda katta. Kichikroq fayl yuklang.";
    const d = err.data;
    if (!d) return `Server xatosi (${err.status}). Keyinroq qayta urinib ko'ring.`;
    if (typeof d.detail === "string") return d.detail;
    return Object.entries(d)
      .map(([key, value]) => {
        const label = FIELD_LABELS[key] ?? key;
        const text = flatten(value).join(" ");
        return label ? `${label}: ${text}` : text;
      })
      .join("\n");
  }

  // Sessiya tugagan bo'lsa login oynasiga qaytaradi
  function handleAuth(err) {
    const isCsrf = typeof err?.data?.detail === "string" && err.data.detail.includes("CSRF");
    if (err instanceof ApiError && (err.status === 401 || err.status === 403) && !isCsrf) {
      state.user = null;
      renderLogin("Sessiya tugadi. Qaytadan kiring.");
      return true;
    }
    return false;
  }

  // ---------- Forma qismlari ----------
  const hintHtml = (hint) => (hint ? `<span class="hint">${esc(hint)}</span>` : "");

  function field(name, label, value = "", opts = {}) {
    const { type = "text", hint = "", required = false, min, max, placeholder = "", maxlength, autocomplete } = opts;
    const attrs = [
      `type="${type}"`,
      `name="${name}"`,
      `value="${esc(value)}"`,
      required ? "required" : "",
      min != null ? `min="${min}"` : "",
      max != null ? `max="${max}"` : "",
      placeholder ? `placeholder="${esc(placeholder)}"` : "",
      maxlength ? `maxlength="${maxlength}"` : "",
      autocomplete ? `autocomplete="${autocomplete}"` : "",
    ].filter(Boolean).join(" ");
    return `<label class="field"><span class="label">${esc(label)}</span><input ${attrs}>${hintHtml(hint)}</label>`;
  }

  function textarea(name, label, value = "", { rows = 5, hint = "", maxlength } = {}) {
    return `<label class="field"><span class="label">${esc(label)}</span>
      <textarea name="${name}" rows="${rows}" ${maxlength ? `maxlength="${maxlength}"` : ""}>${esc(value)}</textarea>${hintHtml(hint)}</label>`;
  }

  function select(name, label, value, options) {
    const items = options
      .map(([v, l]) => `<option value="${esc(v)}" ${v === value ? "selected" : ""}>${esc(l)}</option>`)
      .join("");
    return `<label class="field"><span class="label">${esc(label)}</span><select name="${name}">${items}</select></label>`;
  }

  function checkbox(name, label, checked) {
    return `<label class="check"><input type="checkbox" name="${name}" ${checked ? "checked" : ""}> ${esc(label)}</label>`;
  }

  function fileField(name, label, { accept, multiple = false, required = false, hint = "" } = {}) {
    return `<label class="field"><span class="label">${esc(label)}</span>
      <input type="file" name="${name}" accept="${accept}" ${multiple ? "multiple" : ""} ${required ? "required" : ""}>${hintHtml(hint)}</label>`;
  }

  function imageField(name, label, url, { required = false, removeName = "" } = {}) {
    const preview = url ? `<img src="${esc(url)}" alt="">` : `<span class="muted">Rasm yo'q</span>`;
    return `<div class="field"><span class="label" id="${name}-label">${esc(label)}</span>
      <div class="image-box">
        <div class="image-preview" data-preview-for="${name}">${preview}</div>
        <div class="image-controls">
          <input type="file" name="${name}" accept="${IMAGE_ACCEPT}" aria-labelledby="${name}-label" ${required ? "required" : ""}>
          <span class="hint">JPG, PNG yoki WebP, 15 MB gacha</span>
          ${removeName && url ? checkbox(removeName, "Rasmni olib tashlash", false) : ""}
        </div>
      </div></div>`;
  }

  const formFooter = (submitLabel, extra = "") =>
    `<div class="form-error" hidden></div>
     <div class="form-actions"><button class="btn" type="submit">${esc(submitLabel)}</button>${extra}</div>`;

  function bindPreviews(root) {
    root.querySelectorAll(`input[type="file"][accept="${IMAGE_ACCEPT}"]`).forEach((input) => {
      input.addEventListener("change", () => {
        const box = root.querySelector(`[data-preview-for="${input.name}"]`);
        const file = input.files[0];
        if (box && file) box.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="">`;
      });
    });
  }

  // FormData ni qo'lda yig'amiz: tanlanmagan fayl yuborilmaydi, checkbox true/false bo'ladi
  function collect(form) {
    const data = new FormData();
    for (const el of form.elements) {
      if (!el.name || el.disabled) continue;
      if (el.type === "file") {
        for (const file of el.files) data.append(el.name, file);
      } else if (el.type === "checkbox") {
        data.append(el.name, el.checked ? "true" : "false");
      } else {
        data.append(el.name, el.value);
      }
    }
    return data;
  }

  function onSubmit(form, action, busyLabel = "Saqlanmoqda…") {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('[type="submit"]');
      const errorBox = form.querySelector(".form-error");
      const label = button.textContent;
      errorBox.hidden = true;
      button.disabled = true;
      button.textContent = busyLabel;
      try {
        await action();
      } catch (err) {
        if (handleAuth(err)) return;
        errorBox.textContent = errorText(err);
        errorBox.hidden = false;
      } finally {
        button.disabled = false;
        button.textContent = label;
      }
    });
  }

  // ---------- Kirish ----------
  function renderLogin(message = "") {
    app.innerHTML = `
      <div class="login">
        <form class="card form login-card" id="login-form">
          <div><h1>Admin panel</h1><p class="muted" style="margin:6px 0 0">Muallif saytini boshqarish</p></div>
          ${message ? `<p class="alert">${esc(message)}</p>` : ""}
          ${field("username", "Login", "", { required: true, autocomplete: "username" })}
          ${field("password", "Parol", "", { type: "password", required: true, autocomplete: "current-password" })}
          ${formFooter("Kirish")}
        </form>
      </div>`;
    const form = document.getElementById("login-form");
    form.elements.username.focus();
    onSubmit(
      form,
      async () => {
        state.user = await api("/auth/login/", {
          method: "POST",
          json: { username: form.elements.username.value.trim(), password: form.elements.password.value },
        });
        await router();
      },
      "Kirilmoqda…",
    );
  }

  // ---------- Karkas ----------
  const NAV = [["#/muallif", "Muallif"], ["#/kitoblar", "Kitoblar"], ["#/fikrlar", "Fikrlar"]];

  function renderShell(hash) {
    const section = hash.startsWith("#/kitob") ? "#/kitoblar" : hash.startsWith("#/fikr") ? "#/fikrlar" : hash;
    const links = NAV.map(
      ([href, label]) => `<a href="${href}" ${section === href ? 'aria-current="page"' : ""}>${label}</a>`,
    ).join("");
    app.innerHTML = `
      <div class="shell">
        <aside class="sidebar">
          <div class="sidebar-brand">Admin panel<small>${esc(state.user.name)}</small></div>
          <nav class="nav" aria-label="Bo'limlar">${links}</nav>
          <div class="nav nav-bottom">
            <a href="/" target="_blank" rel="noopener">Saytni ochish ↗</a>
            <button type="button" id="logout">Chiqish</button>
          </div>
        </aside>
        <main class="content" id="view"><p class="muted">Yuklanmoqda…</p></main>
      </div>`;
    document.getElementById("logout").addEventListener("click", async () => {
      try {
        await api("/auth/logout/", { method: "POST" });
      } catch {
        /* baribir chiqamiz */
      }
      state.user = null;
      history.replaceState(null, "", location.pathname);
      renderLogin();
    });
  }

  // ---------- Muallif ----------
  async function viewAuthor(view) {
    const a = await api("/panel/author/");
    view.innerHTML = `
      <header class="view-head">
        <div><h1>Muallif</h1><p class="muted" style="margin:6px 0 0">Saytning birinchi sahifasidagi ma'lumotlar</p></div>
        <a class="btn-ghost" href="/" target="_blank" rel="noopener">Saytda ko'rish ↗</a>
      </header>
      <form class="card form" id="author-form">
        <div class="grid-2">
          ${field("full_name", "Ism familiya", a.full_name, { maxlength: 150 })}
          ${field("academic_degree", "Ilmiy daraja", a.academic_degree, { maxlength: 150, placeholder: "Masalan: fizika-matematika fanlari doktori" })}
          ${field("science_field", "Ilmiy soha", a.science_field, { maxlength: 150 })}
          ${field("email", "Email", a.email, { type: "email" })}
          ${field("telegram", "Telegram", a.telegram, { hint: "@username yoki t.me/username" })}
          ${field("instagram", "Instagram", a.instagram, { hint: "@username yoki havola" })}
        </div>
        ${field("tagline", "Shior (bir jumla)", a.tagline, { maxlength: 255 })}
        ${textarea("bio", "Muallif haqida", a.bio, { rows: 8, hint: "Bo'sh qator bilan xatboshilarga ajrating" })}
        ${imageField("photo", "Muallif rasmi", a.photo, { removeName: "remove_photo" })}
        ${formFooter("Saqlash")}
      </form>`;
    const form = view.querySelector("#author-form");
    bindPreviews(form);
    onSubmit(form, async () => {
      await api("/panel/author/", { method: "PATCH", form: collect(form) });
      toast("Saqlandi");
      await viewAuthor(view);
    });
  }

  // ---------- Kitoblar ----------
  async function viewBooks(view) {
    const books = await api("/panel/books/");
    const list = books
      .map(
        (b) => `
        <a class="card book-item" href="#/kitob/${b.id}">
          <span class="cover-thumb">${b.cover ? `<img src="${esc(b.cover)}" alt="">` : ""}</span>
          <span class="book-item-body">
            <strong>${esc(b.title)}</strong>
            <span class="muted">${b.open_pages_count} / ${b.pages_count} sahifa ochilgan</span>
            ${b.is_published ? '<span class="badge ok">Saytda</span>' : '<span class="badge">Yashirin</span>'}
          </span>
        </a>`,
      )
      .join("");
    view.innerHTML = `
      <header class="view-head">
        <div><h1>Kitoblar</h1><p class="muted" style="margin:6px 0 0">Muqova, annotatsiya va kunma-kun ochiladigan sahifalar</p></div>
        <a class="btn" href="#/kitob/new">+ Yangi kitob</a>
      </header>
      ${books.length ? `<div class="book-list">${list}</div>` : `<div class="card empty">Hali kitob qo'shilmagan. <a href="#/kitob/new">Birinchi kitobni qo'shing</a>.</div>`}`;
  }

  async function viewBook(view, id) {
    const isNew = id === "new";
    const b = isNew
      ? { title: "", annotation: "", cover: null, back_cover: null, spine_color: "", effective_spine_color: "#7a2e22", is_published: true, order: 0 }
      : await api(`/panel/books/${id}/`);

    view.innerHTML = `
      <header class="view-head">
        <div><a class="back" href="#/kitoblar">← Kitoblar</a><h1>${isNew ? "Yangi kitob" : esc(b.title)}</h1></div>
        ${isNew ? "" : `<a class="btn-ghost" href="/kitob/${encodeURIComponent(b.slug)}/" target="_blank" rel="noopener">Saytda ko'rish ↗</a>`}
      </header>
      <form class="card form" id="book-form">
        ${field("title", "Kitob nomi", b.title, { required: true, maxlength: 255 })}
        ${textarea("annotation", "Annotatsiya", b.annotation, { rows: 6, hint: "Kitob sahifasida nom ostida chiqadi" })}
        <div class="grid-2">
          ${imageField("cover", "Muqova rasmi", b.cover, { required: isNew })}
          ${imageField("back_cover", "Orqa muqova (ixtiyoriy)", b.back_cover, { removeName: "remove_back_cover" })}
        </div>
        <p class="hint" style="margin:0">Muqovaga to'liq rasm qo'ying — u 3D kitobning old yuzini butunlay qoplaydi. Eng yaxshi nisbat 5:7, masalan 1500×2100 px.</p>
        <div class="grid-2">
          <fieldset class="field">
            <legend>Kitob qirrasi rangi</legend>
            <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
              <input type="color" id="spine-picker" value="${esc(b.spine_color || b.effective_spine_color)}" ${b.spine_color ? "" : "disabled"} aria-label="Qirra rangi">
              <label class="check"><input type="checkbox" id="spine-auto" ${b.spine_color ? "" : "checked"}> Muqovadan avtomatik</label>
            </div>
          </fieldset>
          <div class="field"><span class="label">Ko'rinish</span>${checkbox("is_published", "Saytda ko'rinsin", b.is_published)}</div>
        </div>
        ${field("order", "Tartib raqami", b.order, { type: "number", min: 0, hint: "Bir nechta kitob bo'lsa, kichik raqamli kitob birinchi chiqadi" })}
        ${formFooter(isNew ? "Kitobni yaratish" : "Saqlash", isNew ? "" : `<button class="btn-danger" type="button" id="delete-book">Kitobni o'chirish</button>`)}
      </form>
      ${isNew ? `<p class="muted">Kitob yaratilgach, shu yerda sahifalarni yuklash bo'limi paydo bo'ladi.</p>` : `<section id="pages" class="form"></section>`}`;

    const form = view.querySelector("#book-form");
    const picker = form.querySelector("#spine-picker");
    const auto = form.querySelector("#spine-auto");
    auto.addEventListener("change", () => {
      picker.disabled = auto.checked;
    });
    bindPreviews(form);

    onSubmit(form, async () => {
      const data = collect(form);
      data.set("spine_color", auto.checked ? "" : picker.value);
      if (isNew) {
        const created = await api("/panel/books/", { method: "POST", form: data });
        toast("Kitob yaratildi. Endi sahifalarni yuklang.");
        location.hash = `#/kitob/${created.id}`;
      } else {
        await api(`/panel/books/${id}/`, { method: "PATCH", form: data });
        toast("Saqlandi");
        await viewBook(view, id);
      }
    });

    if (!isNew) {
      form.querySelector("#delete-book").addEventListener("click", async () => {
        if (!confirm(`«${b.title}» kitobi va uning barcha sahifalari o'chiriladi. Davom etasizmi?`)) return;
        try {
          await api(`/panel/books/${id}/`, { method: "DELETE" });
          toast("Kitob o'chirildi");
          location.hash = "#/kitoblar";
        } catch (err) {
          if (!handleAuth(err)) toast(errorText(err), true);
        }
      });
      await renderPages(view.querySelector("#pages"), b);
    }
  }

  function pageRow(p) {
    const preview = p.thumbnail
      ? `<a href="${esc(p.file)}" target="_blank" rel="noopener" aria-label="${p.number}-sahifani ochish"><img class="thumb" src="${esc(p.thumbnail)}" alt=""></a>`
      : `<a href="${esc(p.file)}" target="_blank" rel="noopener">Ochish</a>`;
    const kind = p.kind === "pdf" ? `PDF${p.pdf_page_count > 1 ? ` · ${p.pdf_page_count} bet` : ""}` : "Rasm";
    return `
      <tr data-id="${p.id}" data-number="${p.number}">
        <td><strong>${p.number}</strong></td>
        <td>${preview}</td>
        <td>${kind}</td>
        <td><input type="datetime-local" value="${toInput(p.publish_at)}" aria-label="${p.number}-sahifa ochilish vaqti"></td>
        <td>${p.is_open ? '<span class="badge ok">Ochiq</span>' : '<span class="badge wait">Kutilmoqda</span>'}</td>
        <td><div class="row-actions">
          <button type="button" class="btn-sm" data-act="save">Vaqtni saqlash</button>
          <label class="btn-sm">Almashtirish<input type="file" class="visually-hidden" accept="${PAGE_ACCEPT}" data-act="replace"></label>
          <button type="button" class="btn-sm danger" data-act="delete">O'chirish</button>
        </div></td>
      </tr>`;
  }

  async function renderPages(section, book) {
    const pages = await api(`/panel/pages/?book=${book.id}`);
    const nextNumber = pages.reduce((max, p) => Math.max(max, p.number), 0) + 1;
    const lastAt = pages.reduce((max, p) => later(max, toInput(p.publish_at)), "");
    const suggested = lastAt ? later(addDays(lastAt, 1), nowInput()) : nowInput();
    const openCount = pages.filter((p) => p.is_open).length;

    section.innerHTML = `
      <header class="view-head sub"><h2>Sahifalar</h2><span class="muted">${openCount} / ${pages.length} ochilgan</span></header>
      <div class="grid-2">
        <form class="card form" id="page-form">
          <div><h3>Bitta sahifa qo'shish</h3><p class="hint" style="margin:4px 0 0">Belgilangan vaqtgacha saytda qulf bilan turadi.</p></div>
          ${field("number", "Sahifa raqami", nextNumber, { type: "number", min: 1, required: true })}
          ${fileField("file", "Fayl", { accept: PAGE_ACCEPT, required: true, hint: "JPG, PNG, WebP yoki PDF, 50 MB gacha" })}
          ${field("publish_at", "Ochilish vaqti", suggested, { type: "datetime-local", required: true })}
          ${formFooter("Qo'shish")}
        </form>
        <form class="card form" id="bulk-form">
          <div><h3>Ko'p sahifani birdan yuklash</h3><p class="hint" style="margin:4px 0 0">Har bir fayl alohida sahifa bo'ladi va navbat bilan ochiladi.</p></div>
          ${fileField("files", "Fayllar", { accept: PAGE_ACCEPT, multiple: true, required: true, hint: "Fayl nomi bo'yicha tartiblanadi: 001.jpg, 002.jpg… Bir martada 100 tagacha." })}
          <div class="grid-2 tight">
            ${field("start_number", "Boshlang'ich raqam", nextNumber, { type: "number", min: 1, required: true })}
            ${field("interval_days", "Har necha kunda bittadan", 1, { type: "number", min: 0, max: 365, required: true, hint: "0 — hammasi birdaniga ochiladi" })}
          </div>
          ${field("start_at", "Birinchisi ochiladigan vaqt", suggested, { type: "datetime-local", required: true })}
          ${formFooter("Yuklash")}
        </form>
      </div>
      ${pages.length
        ? `<div class="card table-wrap"><table class="table">
            <thead><tr><th>№</th><th>Sahifa</th><th>Turi</th><th>Ochilish vaqti</th><th>Holati</th><th><span class="visually-hidden">Amallar</span></th></tr></thead>
            <tbody>${pages.map(pageRow).join("")}</tbody>
          </table></div>`
        : `<div class="card empty">Hali sahifa yuklanmagan.</div>`}`;

    const reload = () => renderPages(section, book);

    const pageForm = section.querySelector("#page-form");
    onSubmit(
      pageForm,
      async () => {
        const data = collect(pageForm);
        data.append("book", book.id);
        await api("/panel/pages/", { method: "POST", form: data });
        toast("Sahifa qo'shildi");
        await reload();
      },
      "Yuklanmoqda…",
    );

    const bulkForm = section.querySelector("#bulk-form");
    onSubmit(
      bulkForm,
      async () => {
        const input = bulkForm.elements.files;
        const files = [...input.files].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
        if (files.length > 100) throw new ApiError(400, { files: ["Bir martada 100 tadan ko'p fayl yuklab bo'lmaydi."] });
        const data = new FormData();
        data.append("book", book.id);
        files.forEach((file) => data.append("files", file));
        for (const name of ["start_number", "interval_days", "start_at"]) data.append(name, bulkForm.elements[name].value);
        const created = await api("/panel/pages/bulk/", { method: "POST", form: data });
        toast(`${created.length} ta sahifa yuklandi`);
        await reload();
      },
      "Yuklanmoqda…",
    );

    const tbody = section.querySelector("tbody");
    if (!tbody) return;

    tbody.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-act]");
      if (!button) return;
      const row = button.closest("tr");
      const { id, number } = row.dataset;
      button.disabled = true;
      try {
        if (button.dataset.act === "save") {
          const value = row.querySelector('input[type="datetime-local"]').value;
          if (!value) {
            toast("Ochilish vaqtini kiriting", true);
            return;
          }
          await api(`/panel/pages/${id}/`, { method: "PATCH", json: { publish_at: value } });
          toast(`${number}-sahifa vaqti saqlandi`);
          await reload();
        } else if (button.dataset.act === "delete") {
          if (!confirm(`${number}-sahifa o'chirilsinmi?`)) return;
          await api(`/panel/pages/${id}/`, { method: "DELETE" });
          toast(`${number}-sahifa o'chirildi`);
          await reload();
        }
      } catch (err) {
        if (!handleAuth(err)) toast(errorText(err), true);
      } finally {
        button.disabled = false;
      }
    });

    tbody.addEventListener("change", async (event) => {
      const input = event.target.closest('input[data-act="replace"]');
      if (!input || !input.files[0]) return;
      const row = input.closest("tr");
      const data = new FormData();
      data.append("file", input.files[0]);
      try {
        await api(`/panel/pages/${row.dataset.id}/`, { method: "PATCH", form: data });
        toast(`${row.dataset.number}-sahifa fayli almashtirildi`);
        await reload();
      } catch (err) {
        if (!handleAuth(err)) toast(errorText(err), true);
      }
    });
  }

  // ---------- Fikrlar ----------
  function postStatus(p) {
    if (!p.is_published) return '<span class="badge">Yashirin</span>';
    if (!p.is_live) return '<span class="badge wait">Rejalashtirilgan</span>';
    return '<span class="badge ok">Saytda</span>';
  }

  async function viewPosts(view) {
    const posts = await api("/panel/posts/");
    const rows = posts
      .map(
        (p) => `<tr>
          <td><a class="title-link" href="#/fikr/${p.id}">${esc(p.title)}</a></td>
          <td>${esc(p.kind_label)}</td>
          <td>${fmtDate(p.published_at)}</td>
          <td>${postStatus(p)}</td>
        </tr>`,
      )
      .join("");
    view.innerHTML = `
      <header class="view-head">
        <div><h1>Fikrlar</h1><p class="muted" style="margin:6px 0 0">Yangiliklar, maqolalar va rasmlar</p></div>
        <a class="btn" href="#/fikr/new">+ Yangi post</a>
      </header>
      ${posts.length
        ? `<div class="card table-wrap"><table class="table"><thead><tr><th>Sarlavha</th><th>Turi</th><th>Sana</th><th>Holati</th></tr></thead><tbody>${rows}</tbody></table></div>`
        : `<div class="card empty">Hali post yo'q. <a href="#/fikr/new">Birinchisini yozing</a>.</div>`}`;
  }

  async function viewPost(view, id) {
    const isNew = id === "new";
    const p = isNew
      ? { title: "", kind: "news", excerpt: "", body: "", image: null, is_published: true, published_at: "" }
      : await api(`/panel/posts/${id}/`);

    view.innerHTML = `
      <header class="view-head">
        <div><a class="back" href="#/fikrlar">← Fikrlar</a><h1>${isNew ? "Yangi post" : esc(p.title)}</h1></div>
        ${isNew ? "" : `<a class="btn-ghost" href="/fikrlar/${encodeURIComponent(p.slug)}/" target="_blank" rel="noopener">Saytda ko'rish ↗</a>`}
      </header>
      <form class="card form" id="post-form">
        ${field("title", "Sarlavha", p.title, { required: true, maxlength: 255 })}
        <div class="grid-2">
          ${select("kind", "Turi", p.kind, KINDS)}
          ${field("published_at", "E'lon vaqti", p.published_at ? toInput(p.published_at) : nowInput(), { type: "datetime-local", required: true, hint: "Kelajakdagi vaqt qo'ysangiz, post o'sha vaqtda chiqadi" })}
        </div>
        ${textarea("excerpt", "Qisqa tavsif", p.excerpt, { rows: 2, maxlength: 300, hint: "Ro'yxatda sarlavha ostida chiqadi. Bo'sh qolsa, matn boshidan olinadi." })}
        ${textarea("body", "Matn", p.body, { rows: 14, hint: "Bo'sh qator bilan xatboshilarga ajrating" })}
        ${imageField("image", "Rasm", p.image, { removeName: "remove_image" })}
        ${checkbox("is_published", "Saytda ko'rinsin", p.is_published)}
        ${formFooter(isNew ? "E'lon qilish" : "Saqlash", isNew ? "" : `<button class="btn-danger" type="button" id="delete-post">O'chirish</button>`)}
      </form>`;

    const form = view.querySelector("#post-form");
    bindPreviews(form);
    onSubmit(form, async () => {
      const data = collect(form);
      if (isNew) {
        const created = await api("/panel/posts/", { method: "POST", form: data });
        toast("Post saqlandi");
        location.hash = `#/fikr/${created.id}`;
      } else {
        await api(`/panel/posts/${id}/`, { method: "PATCH", form: data });
        toast("Saqlandi");
        await viewPost(view, id);
      }
    });

    if (!isNew) {
      form.querySelector("#delete-post").addEventListener("click", async () => {
        if (!confirm(`«${p.title}» o'chirilsinmi?`)) return;
        try {
          await api(`/panel/posts/${id}/`, { method: "DELETE" });
          toast("Post o'chirildi");
          location.hash = "#/fikrlar";
        } catch (err) {
          if (!handleAuth(err)) toast(errorText(err), true);
        }
      });
    }
  }

  // ---------- Router ----------
  const ROUTES = [
    [/^#\/muallif$/, viewAuthor],
    [/^#\/kitoblar$/, viewBooks],
    [/^#\/kitob\/(new|\d+)$/, viewBook],
    [/^#\/fikrlar$/, viewPosts],
    [/^#\/fikr\/(new|\d+)$/, viewPost],
  ];

  async function router() {
    if (!state.user) {
      try {
        state.user = await api("/auth/me/");
      } catch {
        renderLogin();
        return;
      }
    }
    const hash = location.hash || "#/muallif";
    const route = ROUTES.find(([pattern]) => pattern.test(hash));
    if (!route) {
      location.hash = "#/muallif";
      return;
    }
    renderShell(hash);
    const view = document.getElementById("view");
    try {
      await route[1](view, hash.match(route[0])[1]);
    } catch (err) {
      if (handleAuth(err)) return;
      view.innerHTML = `<div class="card form"><p class="form-error">${esc(errorText(err))}</p><div><a class="btn-ghost" href="#/muallif">Bosh bo'limga</a></div></div>`;
    }
  }

  window.addEventListener("hashchange", router);
  router();
})();
