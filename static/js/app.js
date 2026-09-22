/* ==========================================================
   Конф+ — SPA-клиент
   ========================================================== */

const API = "/api";

const ROLE_LABELS = {
  participant: "Участник",
  speaker: "Спикер",
  admin: "Администратор",
};

const STATUS_LABELS = {
  pending: "На рассмотрении",
  approved: "Утверждён",
  rejected: "Отклонён",
  registered: "Зарегистрирован",
  sent: "Отправлено",
  accepted: "Принято",
  declined: "Отклонено",
  unpaid: "Не оплачен",
  paid: "Оплачено",
  requested: "Запрошено",
  confirmed: "Подтверждено",
  cancelled: "Отменено",
  queued: "В очереди",
};

const state = {
  token: localStorage.getItem("confplus_token") || null,
  user: null,
  section: "conferences",
  conferences: [],
};

/* ---------------- helpers ---------------- */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined && v !== false) node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c === null || c === undefined || c === false) continue;
    node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function fmtDateTime(v) {
  if (!v) return "—";
  const d = new Date(v);
  if (isNaN(d)) return v;
  return d.toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtDate(v) {
  if (!v) return "—";
  const d = new Date(v);
  if (isNaN(d)) return d.toLocaleDateString("ru-RU");
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function toLocalInput(dt) {
  const d = new Date(dt);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toast(message, type = "info") {
  const node = el("div", { class: `toast ${type}` }, [message]);
  $("#toasts").appendChild(node);
  setTimeout(() => {
    node.style.opacity = "0";
    node.style.transform = "translateX(40px)";
    node.style.transition = ".3s";
    setTimeout(() => node.remove(), 320);
  }, 3800);
}

function statusBadge(status) {
  const map = {
    approved: "success", paid: "success", accepted: "success", confirmed: "success",
    pending: "warn", requested: "warn", queued: "warn", unpaid: "warn",
    rejected: "danger", declined: "danger", cancelled: "danger",
    registered: "neutral", sent: "neutral",
  };
  return el("span", { class: `badge ${map[status] || "neutral"}` }, [STATUS_LABELS[status] || status]);
}

/* ---------------- API ---------------- */

async function api(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) headers["Authorization"] = `Bearer ${state.token}`;

  let res;
  try {
    res = await fetch(API + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new Error("Нет соединения с сервером");
  }

  if (res.status === 204) return null;

  const text = await res.text();
  let data = null;
  if (text) { try { data = JSON.parse(text); } catch { data = text; } }

  if (!res.ok) {
    if (res.status === 401 && auth) {
      logout(false);
      throw new Error("Сессия истекла, войдите заново");
    }
    let msg = "Ошибка запроса";
    if (data && data.detail) {
      msg = typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
          : JSON.stringify(data.detail);
    }
    throw new Error(msg);
  }
  return data;
}

/* ---------------- auth flow ---------------- */

function showAuth() {
  $("#auth-screen").classList.remove("hidden");
  $("#app-screen").classList.add("hidden");
}

function showApp() {
  $("#auth-screen").classList.add("hidden");
  $("#app-screen").classList.remove("hidden");

  $("#user-name").textContent = state.user.full_name;
  const roleBadge = $("#user-role");
  roleBadge.textContent = ROLE_LABELS[state.user.role] || state.user.role;
  roleBadge.className = "badge " + (state.user.role === "admin" ? "success" : state.user.role === "speaker" ? "warn" : "neutral");

  // Скрываем разделы по ролям
  $$(".admin-only").forEach((n) => n.classList.toggle("hidden", state.user.role !== "admin"));
  $$(".speaker-admin-only").forEach((n) => n.classList.toggle("hidden", state.user.role === "participant"));

  // Если текущий раздел недоступен — переключимся на конференции
  if (state.section === "abstracts" && state.user.role === "participant") {
    state.section = "conferences";
    $$(".nav-item").forEach((n) => n.classList.remove("active"));
    const confBtn = $$(".nav-item").find((n) => n.dataset.section === "conferences");
    if (confBtn) confBtn.classList.add("active");
  }
  if (state.section === "reports" && state.user.role !== "admin") {
    state.section = "conferences";
  }

  renderSection(state.section);
}

function logout(notify = true) {
  state.token = null;
  state.user = null;
  localStorage.removeItem("confplus_token");
  showAuth();
  if (notify) toast("Вы вышли из системы", "success");
}

/* ---------------- boot ---------------- */

document.addEventListener("DOMContentLoaded", () => {
  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const isLogin = tab.dataset.tab === "login";
      $("#login-form").classList.toggle("hidden", !isLogin);
      $("#register-form").classList.toggle("hidden", isLogin);
    });
  });

  $("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const data = await api("/auth/login", {
        method: "POST",
        auth: false,
        body: { email: fd.get("email"), password: fd.get("password") },
      });
      state.token = data.access_token;
      state.user = data.user;
      localStorage.setItem("confplus_token", state.token);
      toast(`Добро пожаловать, ${data.user.full_name}!`, "success");
      showApp();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("#register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const data = await api("/auth/register", {
        method: "POST",
        auth: false,
        body: {
          full_name: fd.get("full_name"),
          email: fd.get("email"),
          password: fd.get("password"),
          role: fd.get("role"),
          consent_152fz: fd.get("consent_152fz") === "on",
        },
      });
      state.token = data.access_token;
      state.user = data.user;
      localStorage.setItem("confplus_token", state.token);
      toast("Аккаунт успешно создан", "success");
      showApp();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("#logout-btn").addEventListener("click", () => logout());

  $$(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      if (item.classList.contains("hidden")) return;
      $$(".nav-item").forEach((n) => n.classList.remove("active"));
      item.classList.add("active");
      state.section = item.dataset.section;
      renderSection(state.section);
    });
  });

  $("#modal").addEventListener("click", (e) => {
    if (e.target.id === "modal") closeModal();
  });

  if (state.token) {
    api("/auth/me")
      .then((user) => {
        state.user = user;
        showApp();
      })
      .catch(() => {
        state.token = null;
        localStorage.removeItem("confplus_token");
        showAuth();
      });
  } else {
    showAuth();
  }
});

/* ---------------- modal ---------------- */

function openModal(title, bodyNode) {
  $("#modal-title").textContent = title;
  const body = $("#modal-body");
  body.innerHTML = "";
  body.appendChild(bodyNode);
  $("#modal").classList.remove("hidden");
}

function closeModal() {
  $("#modal").classList.add("hidden");
}

/* ---------------- section router ---------------- */

function renderSection(section) {
  const content = $("#content");
  content.innerHTML = "";

  const map = {
    conferences: renderConferences,
    registrations: renderRegistrations,
    abstracts: renderAbstracts,
    ratings: renderRatings,
    invitations: renderInvitations,
    fees: renderFees,
    hotels: renderHotels,
    mailings: renderMailings,
    reports: renderReports,
    profile: renderProfile,
  };

  (map[section] || renderConferences)(content).catch((e) => {
    content.appendChild(el("div", { class: "empty" }, [e.message]));
  });
}

/* ================= КОНФЕРЕНЦИИ ================= */

async function renderConferences(root) {
  const confs = await api("/conferences", { auth: false });
  state.conferences = confs;

  root.appendChild(el("div", { class: "page-head" }, [
    el("h2", {}, ["Конференции"]),
    state.user.role === "admin"
      ? el("button", { class: "btn primary", onclick: () => openConferenceModal() }, ["+ Создать конференцию"])
      : null,
  ]));

  if (!confs.length) {
    root.appendChild(el("div", { class: "empty" }, ["Пока нет ни одной конференции"]));
    return;
  }

  const now = new Date();
  const grid = el("div", { class: "grid" });
  confs.forEach((c) => {
    const isFinished = new Date(c.end_date) < now;
    const card = el("div", { class: "card" }, [
      el("h3", {}, [esc(c.title)]),
      el("div", { class: "meta" }, [
        el("span", {}, [`📍 ${esc(c.location || "—")}`]),
        el("span", {}, [`🗓 ${fmtDateTime(c.start_date)} → ${fmtDateTime(c.end_date)}`]),
        isFinished
          ? el("span", { class: "badge neutral" }, ["Завершена"])
          : el("span", { class: "badge success" }, ["Активна"]),
        c.registration_deadline
          ? el("span", {}, [`⏳ Регистрация до: ${fmtDateTime(c.registration_deadline)}`])
          : el("span", {}, ["⏳ Регистрация до начала"]),
      ]),
      c.description ? el("p", { class: "desc" }, [esc(c.description)]) : null,
      el("div", { class: "actions" }, [
        !isFinished
          ? el("button", { class: "btn success small", onclick: () => registerOnConference(c.id) }, ["Записаться"])
          : null,
        el("button", { class: "btn ghost small", onclick: () => viewConferenceAbstracts(c) }, ["Доклады"]),
        state.user.role === "admin" && !isFinished
          ? el("button", { class: "btn warn small", onclick: () => finishConference(c.id) }, ["Завершить"])
          : null,
        state.user.role === "admin"
          ? el("button", { class: "btn ghost small", onclick: () => openConferenceModal(c) }, ["Изменить"])
          : null,
        state.user.role === "admin"
          ? el("button", { class: "btn danger small", onclick: () => deleteConference(c.id) }, ["Удалить"])
          : null,
      ]),
    ]);
    grid.appendChild(card);
  });
  root.appendChild(grid);
}

function openConferenceModal(conf = null) {
  if (conf && (conf.id === undefined || conf.id === null || conf instanceof Event)) {
    conf = null;
  }

  const form = el("form", { class: "form" }, [
    el("label", {}, ["Название", el("input", { name: "title", required: true, value: conf?.title || "" })]),
    el("label", {}, ["Место", el("input", { name: "location", value: conf?.location || "", placeholder: "Москва, ..." })]),
    el("label", {}, ["Описание", el("textarea", { name: "description" }, [conf?.description || ""])]),
    el("label", {}, ["Дата начала", el("input", { type: "datetime-local", name: "start_date", required: true, value: conf ? toLocalInput(conf.start_date) : "" })]),
    el("label", {}, ["Дата окончания", el("input", { type: "datetime-local", name: "end_date", required: true, value: conf ? toLocalInput(conf.end_date) : "" })]),
    el("label", {}, ["Дедлайн регистрации (необязательно)", el("input", { type: "datetime-local", name: "registration_deadline", value: conf?.registration_deadline ? toLocalInput(conf.registration_deadline) : "" })]),
    el("div", { class: "actions" }, [
      el("button", { type: "submit", class: "btn primary" }, [conf ? "Сохранить" : "Создать"]),
      el("button", { type: "button", class: "btn ghost", onclick: closeModal }, ["Отмена"]),
    ]),
  ]);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const payload = {
      title: fd.get("title"),
      location: fd.get("location") || "",
      description: fd.get("description") || "",
      start_date: fd.get("start_date"),
      end_date: fd.get("end_date"),
      registration_deadline: fd.get("registration_deadline") || null,
    };
    try {
      if (conf) {
        await api(`/conferences/${conf.id}`, { method: "PATCH", body: payload });
        toast("Конференция обновлена", "success");
      } else {
        await api("/conferences", { method: "POST", body: payload });
        toast("Конференция создана", "success");
      }
      closeModal();
      renderSection("conferences");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  openModal(conf ? "Редактирование конференции" : "Новая конференция", form);
}

async function deleteConference(id) {
  if (!confirm("Удалить конференцию со всеми связанными данными?")) return;
  try {
    await api(`/conferences/${id}`, { method: "DELETE" });
    toast("Конференция удалена", "success");
    renderSection("conferences");
  } catch (e) {
    toast(e.message, "error");
  }
}

async function finishConference(id) {
  if (!confirm("Завершить конференцию принудительно? После этого участники смогут ставить оценки.")) return;
  try {
    await api(`/conferences/${id}/finish`, { method: "POST" });
    toast("Конференция завершена", "success");
    renderSection("conferences");
  } catch (e) {
    toast(e.message, "error");
  }
}

async function registerOnConference(id) {
  try {
    await api(`/conferences/${id}/registrations`, { method: "POST" });
    toast("Вы зарегистрированы на конференцию", "success");
  } catch (e) {
    toast(e.message, "error");
  }
}

async function viewConferenceAbstracts(conf) {
  try {
    const list = await api(`/conferences/${conf.id}/abstracts`, { auth: false });
    const wrap = el("div");
    if (!list.length) {
      wrap.appendChild(el("div", { class: "empty" }, ["Докладов пока нет"]));
    } else {
      list.forEach((a) => {
        wrap.appendChild(el("div", { class: "card", style: "margin-bottom:12px" }, [
          el("h3", {}, [esc(a.title)]),
          el("div", { class: "meta" }, [
            el("span", {}, [`⏱ ${a.duration_minutes} мин`]),
            el("span", {}, [`📅 ${fmtDateTime(a.submitted_at)}`]),
            statusBadge(a.status),
          ]),
          el("p", { class: "desc" }, [esc(a.content)]),
        ]));
      });
    }
    openModal(`Доклады — ${conf.title}`, wrap);
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ================= МОИ РЕГИСТРАЦИИ ================= */

async function renderRegistrations(root) {
  const regs = await api("/registrations/my");
  root.appendChild(el("div", { class: "page-head" }, [el("h2", {}, ["Мои регистрации"])]));

  if (!regs.length) {
    root.appendChild(el("div", { class: "empty" }, ["Вы пока не зарегистрированы ни на одну конференцию"]));
    return;
  }

  const confs = await api("/conferences", { auth: false });
  const byId = Object.fromEntries(confs.map((c) => [c.id, c]));

  const wrap = el("div", { class: "table-wrap" });
  const table = el("table");
  table.appendChild(el("thead", {}, [el("tr", {}, [
    el("th", {}, ["Конференция"]), el("th", {}, ["Дата регистрации"]), el("th", {}, ["Статус"]), el("th", {}, ["Действия"]),
  ])]));
  const tbody = el("tbody");
  regs.forEach((r) => {
    tbody.appendChild(el("tr", {}, [
      el("td", {}, [esc(byId[r.conference_id]?.title || `#${r.conference_id}`)]),
      el("td", {}, [fmtDateTime(r.registered_at)]),
      el("td", {}, [statusBadge(r.status)]),
      el("td", {}, [el("button", { class: "btn danger small", onclick: () => cancelReg(r.id) }, ["Отменить"])]),
    ]));
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  root.appendChild(wrap);
}

async function cancelReg(id) {
  if (!confirm("Отменить регистрацию?")) return;
  try {
    await api(`/registrations/${id}`, { method: "DELETE" });
    toast("Регистрация отменена", "success");
    renderSection("registrations");
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ================= ДОКЛАДЫ ================= */

async function renderAbstracts(root) {
  const confs = await api("/conferences", { auth: false });
  const canSubmit = state.user.role === "speaker" || state.user.role === "admin";

  root.appendChild(el("div", { class: "page-head" }, [
    el("h2", {}, ["Доклады и тезисы"]),
    canSubmit ? el("button", { class: "btn primary", onclick: () => openAbstractModal(confs) }, ["+ Подать доклад"]) : null,
  ]));

  const mine = await api("/abstracts/my");

  if (!mine.length) {
    root.appendChild(el("div", { class: "empty" }, ["У вас пока нет поданных докладов"]));
  } else {
    const grid = el("div", { class: "grid" });
    mine.forEach((a) => {
      const conf = confs.find((c) => c.id === a.conference_id);
      grid.appendChild(el("div", { class: "card" }, [
        el("h3", {}, [esc(a.title)]),
        el("div", { class: "meta" }, [
          el("span", {}, [`📅 ${esc(conf?.title || `#${a.conference_id}`)}`]),
          el("span", {}, [`⏱ ${a.duration_minutes} мин`]),
          statusBadge(a.status),
        ]),
        el("p", { class: "desc" }, [esc(a.content.slice(0, 220)) + (a.content.length > 220 ? "…" : "")]),
        el("div", { class: "actions" }, [
          a.status === "pending" ? el("button", { class: "btn ghost small", onclick: () => openAbstractModal(confs, a) }, ["Изменить"]) : null,
          el("button", { class: "btn danger small", onclick: () => deleteAbstract(a.id) }, ["Удалить"]),
          state.user.role === "admin" && a.status === "pending" ? el("button", { class: "btn success small", onclick: () => moderate(a.id, "approve") }, ["Утвердить"]) : null,
          state.user.role === "admin" && a.status === "pending" ? el("button", { class: "btn danger small", onclick: () => moderate(a.id, "reject") }, ["Отклонить"]) : null,
        ]),
      ]));
    });
    root.appendChild(grid);
  }

  if (state.user.role === "admin" && confs.length) {
    root.appendChild(el("div", { class: "page-head", style: "margin-top:30px" }, [el("h2", {}, ["Все доклады"])]));
    for (const c of confs) {
      const list = await api(`/conferences/${c.id}/abstracts`, { auth: false });
      if (!list.length) continue;
      root.appendChild(el("h3", { style: "margin:14px 0 8px" }, [`${esc(c.title)} (${list.length})`]));
      const wrap = el("div", { class: "table-wrap" });
      const t = el("table");
      t.appendChild(el("thead", {}, [el("tr", {}, [
        el("th", {}, ["Название"]), el("th", {}, ["Длительность"]), el("th", {}, ["Статус"]), el("th", {}, ["Действия"]),
      ])]));
      const tb = el("tbody");
      list.forEach((a) => {
        tb.appendChild(el("tr", {}, [
          el("td", {}, [esc(a.title)]),
          el("td", {}, [`${a.duration_minutes} мин`]),
          el("td", {}, [statusBadge(a.status)]),
          el("td", {}, [
            a.status === "pending" ? el("button", { class: "btn success small", onclick: () => moderate(a.id, "approve") }, ["Утвердить"]) : null,
            a.status === "pending" ? el("button", { class: "btn danger small", onclick: () => moderate(a.id, "reject") }, ["Отклонить"]) : null,
          ]),
        ]));
      });
      t.appendChild(tb);
      wrap.appendChild(t);
      root.appendChild(wrap);
    }
  }
}

function openAbstractModal(confs, abstract = null) {
  const form = el("form", { class: "form" }, [
    el("label", {}, ["Конференция", (() => {
      const sel = el("select", { name: "conference_id", required: true });
      confs.forEach((c) => {
        const o = el("option", { value: c.id }, [c.title]);
        if (abstract && abstract.conference_id === c.id) o.selected = true;
        sel.appendChild(o);
      });
      return sel;
    })()]),
    el("label", {}, ["Название доклада", el("input", { name: "title", required: true, value: abstract?.title || "" })]),
    el("label", {}, ["Тезисы / содержание", el("textarea", { name: "content", required: true, minlength: 10 }, [abstract?.content || ""])]),
    el("label", {}, ["Длительность, мин (> 0)", el("input", { type: "number", name: "duration_minutes", min: 1, max: 600, required: true, value: abstract?.duration_minutes || 30 })]),
    el("div", { class: "actions" }, [
      el("button", { type: "submit", class: "btn primary" }, [abstract ? "Сохранить" : "Подать заявку"]),
      el("button", { type: "button", class: "btn ghost", onclick: closeModal }, ["Отмена"]),
    ]),
  ]);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const payload = {
      title: fd.get("title"),
      content: fd.get("content"),
      duration_minutes: Number(fd.get("duration_minutes")),
    };
    try {
      if (abstract) {
        await api(`/abstracts/${abstract.id}`, { method: "PATCH", body: payload });
        toast("Доклад обновлён", "success");
      } else {
        await api("/abstracts", { method: "POST", body: { ...payload, conference_id: Number(fd.get("conference_id")) } });
        toast("Заявка отправлена на рассмотрение", "success");
      }
      closeModal();
      renderSection("abstracts");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  openModal(abstract ? "Редактирование доклада" : "Подача доклада", form);
}

async function deleteAbstract(id) {
  if (!confirm("Удалить доклад?")) return;
  try {
    await api(`/abstracts/${id}`, { method: "DELETE" });
    toast("Доклад удалён", "success");
    renderSection("abstracts");
  } catch (e) { toast(e.message, "error"); }
}

async function moderate(id, action) {
  try {
    await api(`/abstracts/${id}/${action}`, { method: "POST" });
    toast("Статус доклада обновлён", "success");
    renderSection("abstracts");
  } catch (e) { toast(e.message, "error"); }
}

/* ================= ОЦЕНКИ ================= */

async function renderRatings(root) {
  const confs = await api("/conferences", { auth: false });
  root.appendChild(el("div", { class: "page-head" }, [el("h2", {}, ["Оценки докладов"])]));

  if (!confs.length) {
    root.appendChild(el("div", { class: "empty" }, ["Нет доступных конференций"]));
    return;
  }

  for (const c of confs) {
    const list = await api(`/conferences/${c.id}/abstracts`, { auth: false });
    if (!list.length) continue;

    root.appendChild(el("h3", { style: "margin:20px 0 10px" }, [esc(c.title)]));
    const now = new Date();
    const finished = new Date(c.end_date) < now;
    if (!finished) {
      root.appendChild(el("p", { class: "muted small" }, ["Оценка станет доступна после завершения конференции"]));
    }

    const wrap = el("div", { class: "table-wrap" });
    const t = el("table");
    t.appendChild(el("thead", {}, [el("tr", {}, [
      el("th", {}, ["Доклад"]), el("th", {}, ["Длит."]), el("th", {}, ["Оценить"]),
    ])]));
    const tb = el("tbody");
    list.forEach((a) => {
      const canRate = finished && a.author_id !== state.user.id;
      tb.appendChild(el("tr", {}, [
        el("td", {}, [esc(a.title)]),
        el("td", {}, [`${a.duration_minutes} мин`]),
        el("td", {}, [
          canRate
            ? el("button", { class: "btn ghost small", onclick: () => openRatingModal(a) }, ["Оценить"])
            : el("span", { class: "muted small" }, [finished ? "—" : "до завершения"]),
        ]),
      ]));
    });
    t.appendChild(tb);
    wrap.appendChild(t);
    root.appendChild(wrap);
  }
}

function openRatingModal(abstract) {
  const form = el("form", { class: "form" }, [
    el("p", { class: "muted" }, [esc(abstract.title)]),
    el("label", {}, ["Оценка (1–5)", (() => {
      const sel = el("select", { name: "score", required: true });
      [1, 2, 3, 4, 5].forEach((n) => sel.appendChild(el("option", { value: n, selected: n === 5 }, [String(n)])));
      return sel;
    })()]),
    el("label", {}, ["Отзыв (необязательно)", el("textarea", { name: "review", maxlength: 2000 })]),
    el("div", { class: "actions" }, [
      el("button", { type: "submit", class: "btn primary" }, ["Отправить оценку"]),
      el("button", { type: "button", class: "btn ghost", onclick: closeModal }, ["Отмена"]),
    ]),
  ]);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    try {
      await api(`/abstracts/${abstract.id}/ratings`, {
        method: "POST",
        body: { score: Number(fd.get("score")), review: fd.get("review") || null },
      });
      toast("Оценка сохранена", "success");
      closeModal();
      renderSection("ratings");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  openModal("Оценка доклада", form);
}

/* ================= ПРИГЛАШЕНИЯ ================= */

async function renderInvitations(root) {
  root.appendChild(el("div", { class: "page-head" }, [el("h2", {}, ["Приглашения"])]));

  if (state.user.role === "admin") {
    root.appendChild(el("button", { class: "btn primary", style: "margin-bottom:14px", onclick: () => openInvitationModal() }, ["+ Создать приглашение"]));
  }

  const list = await api("/invitations/my");
  if (!list.length) {
    root.appendChild(el("div", { class: "empty" }, ["Приглашений нет"]));
    return;
  }

  const confs = await api("/conferences", { auth: false });
  const byId = Object.fromEntries(confs.map((c) => [c.id, c]));

  const wrap = el("div", { class: "table-wrap" });
  const t = el("table");
  t.appendChild(el("thead", {}, [el("tr", {}, [
    el("th", {}, ["Конференция"]), el("th", {}, ["Отправлено"]), el("th", {}, ["Статус"]), el("th", {}, ["Действия"]),
  ])]));
  const tb = el("tbody");
  list.forEach((i) => {
    tb.appendChild(el("tr", {}, [
      el("td", {}, [esc(byId[i.conference_id]?.title || `#${i.conference_id}`)]),
      el("td", {}, [fmtDateTime(i.sent_at)]),
      el("td", {}, [statusBadge(i.status)]),
      el("td", {}, [
        i.status === "sent" ? el("button", { class: "btn success small", onclick: () => setInvitation(i.id, "accepted") }, ["Принять"]) : null,
        i.status === "sent" ? el("button", { class: "btn danger small", onclick: () => setInvitation(i.id, "declined") }, ["Отклонить"]) : null,
      ]),
    ]));
  });
  t.appendChild(tb);
  wrap.appendChild(t);
  root.appendChild(wrap);
}

async function setInvitation(id, status) {
  try {
    await api(`/invitations/${id}`, { method: "PATCH", body: { status } });
    toast("Статус приглашения обновлён", "success");
    renderSection("invitations");
  } catch (e) { toast(e.message, "error"); }
}

async function openInvitationModal() {
  const confs = await api("/conferences", { auth: false });
  const form = el("form", { class: "form" }, [
    el("label", {}, ["Конференция", (() => {
      const sel = el("select", { name: "conference_id", required: true });
      confs.forEach((c) => sel.appendChild(el("option", { value: c.id }, [c.title])));
      return sel;
    })()]),
    el("label", {}, ["ID пользователя (participant_id)", el("input", { type: "number", name: "participant_id", required: true })]),
    el("div", { class: "actions" }, [
      el("button", { type: "submit", class: "btn primary" }, ["Отправить"]),
      el("button", { type: "button", class: "btn ghost", onclick: closeModal }, ["Отмена"]),
    ]),
  ]);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    try {
      await api("/invitations", {
        method: "POST",
        body: { conference_id: Number(fd.get("conference_id")), participant_id: Number(fd.get("participant_id")) },
      });
      toast("Приглашение создано", "success");
      closeModal();
      renderSection("invitations");
    } catch (err) { toast(err.message, "error"); }
  });
  openModal("Новое приглашение", form);
}

/* ================= ОРГВЗНОСЫ ================= */

async function renderFees(root) {
  const confs = await api("/conferences", { auth: false });
  root.appendChild(el("div", { class: "page-head" }, [
    el("h2", {}, ["Оргвзносы"]),
    el("button", { class: "btn primary", onclick: () => openFeeModal(confs) }, ["+ Создать оргвзнос"]),
  ]));

  const list = await api("/fees/my");
  if (!list.length) {
    root.appendChild(el("div", { class: "empty" }, ["Оргвзносов нет"]));
    return;
  }
  const byId = Object.fromEntries(confs.map((c) => [c.id, c]));

  const wrap = el("div", { class: "table-wrap" });
  const t = el("table");
  t.appendChild(el("thead", {}, [el("tr", {}, [
    el("th", {}, ["Конференция"]), el("th", {}, ["Сумма"]), el("th", {}, ["Статус"]), el("th", {}, ["Оплачен"]), el("th", {}, ["Действия"]),
  ])]));
  const tb = el("tbody");
  list.forEach((f) => {
    tb.appendChild(el("tr", {}, [
      el("td", {}, [esc(byId[f.conference_id]?.title || `#${f.conference_id}`)]),
      el("td", {}, [`${f.amount.toFixed(2)} ₽`]),
      el("td", {}, [statusBadge(f.status)]),
      el("td", {}, [fmtDateTime(f.paid_at)]),
      el("td", {}, [
        f.status !== "paid" ? el("button", { class: "btn success small", onclick: () => payFee(f.id) }, ["Оплатить"]) : null,
      ]),
    ]));
  });
  t.appendChild(tb);
  wrap.appendChild(t);
  root.appendChild(wrap);
}

async function payFee(id) {
  try {
    await api(`/fees/${id}/pay`, { method: "POST" });
    toast("Оргвзнос оплачен", "success");
    renderSection("fees");
  } catch (e) { toast(e.message, "error"); }
}

function openFeeModal(confs) {
  const form = el("form", { class: "form" }, [
    el("label", {}, ["Конференция", (() => {
      const sel = el("select", { name: "conference_id", required: true });
      confs.forEach((c) => sel.appendChild(el("option", { value: c.id }, [c.title])));
      return sel;
    })()]),
    state.user.role === "admin"
      ? el("label", {}, ["ID участника (пусто = себе)", el("input", { type: "number", name: "participant_id" })])
      : null,
    el("label", {}, ["Сумма, ₽", el("input", { type: "number", step: "0.01", min: "0.01", name: "amount", required: true })]),
    el("div", { class: "actions" }, [
      el("button", { type: "submit", class: "btn primary" }, ["Создать"]),
      el("button", { type: "button", class: "btn ghost", onclick: closeModal }, ["Отмена"]),
    ]),
  ]);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const pid = fd.get("participant_id");
    try {
      await api("/fees", {
        method: "POST",
        body: {
          conference_id: Number(fd.get("conference_id")),
          participant_id: pid ? Number(pid) : null,
          amount: Number(fd.get("amount")),
        },
      });
      toast("Оргвзнос создан", "success");
      closeModal();
      renderSection("fees");
    } catch (err) { toast(err.message, "error"); }
  });
  openModal("Новый оргвзнос", form);
}

/* ================= ГОСТИНИЦА ================= */

async function renderHotels(root) {
  const confs = await api("/conferences", { auth: false });
  const isAdmin = state.user.role === "admin";

  root.appendChild(el("div", { class: "page-head" }, [
    el("h2", {}, ["Гостиница"]),
    el("button", { class: "btn primary", onclick: () => openHotelModal(confs) }, ["+ Запросить проживание"]),
  ]));

  // Счётчик мест
  try {
    const cap = await api("/hotels/capacity");
    root.appendChild(el("div", { class: "stats", style: "margin-bottom:22px" }, [
      el("div", { class: "stat" }, [
        el("div", { class: "label" }, ["Всего мест"]),
        el("div", { class: "value" }, [String(cap.capacity)]),
      ]),
      el("div", { class: "stat" }, [
        el("div", { class: "label" }, ["Занято"]),
        el("div", { class: "value" }, [String(cap.occupied)]),
      ]),
      el("div", { class: "stat" }, [
        el("div", { class: "label" }, ["Свободно"]),
        el("div", { class: "value" }, [String(cap.available)]),
      ]),
    ]));
  } catch { /* не критично */ }

  const list = isAdmin ? await api("/hotels") : await api("/hotels/my");
  if (!list.length) {
    root.appendChild(el("div", { class: "empty" }, [isAdmin ? "Заявок на проживание нет" : "Ваших заявок нет"]));
    return;
  }
  const byId = Object.fromEntries(confs.map((c) => [c.id, c]));

  const wrap = el("div", { class: "table-wrap" });
  const t = el("table");
  t.appendChild(el("thead", {}, [el("tr", {}, [
    ...(isAdmin ? [el("th", {}, ["ID участника"])] : []),
    el("th", {}, ["Конференция"]), el("th", {}, ["Заезд"]), el("th", {}, ["Выезд"]), el("th", {}, ["Статус"]), el("th", {}, ["Действия"]),
  ])]));
  const tb = el("tbody");
  list.forEach((h) => {
    const actions = [];
    if (isAdmin) {
      if (h.status === "requested") {
        actions.push(el("button", { class: "btn success small", onclick: () => confirmHotel(h.id) }, ["Подтвердить"]));
      }
      if (h.status === "confirmed") {
        actions.push(el("button", { class: "btn warn small", onclick: () => checkoutHotel(h.id) }, ["Выселить"]));
      }
    } else {
      if (h.status !== "cancelled") {
        actions.push(el("button", { class: "btn danger small", onclick: () => cancelHotel(h.id) }, ["Отменить"]));
      }
    }
    tb.appendChild(el("tr", {}, [
      ...(isAdmin ? [el("td", {}, [String(h.participant_id)])] : []),
      el("td", {}, [esc(byId[h.conference_id]?.title || `#${h.conference_id}`)]),
      el("td", {}, [fmtDate(h.check_in)]),
      el("td", {}, [fmtDate(h.check_out)]),
      el("td", {}, [statusBadge(h.status)]),
      el("td", {}, actions.length ? actions : [el("span", { class: "muted small" }, ["—"])]),
    ]));
  });
  t.appendChild(tb);
  wrap.appendChild(t);
  root.appendChild(wrap);
}

async function cancelHotel(id) {
  try {
    await api(`/hotels/${id}`, { method: "PATCH", body: { status: "cancelled" } });
    toast("Бронирование отменено", "success");
    renderSection("hotels");
  } catch (e) { toast(e.message, "error"); }
}

async function confirmHotel(id) {
  try {
    await api(`/hotels/${id}/confirm`, { method: "POST" });
    toast("Заявка подтверждена", "success");
    renderSection("hotels");
  } catch (e) { toast(e.message, "error"); }
}

async function checkoutHotel(id) {
  if (!confirm("Принудительно выселить участника? Место освободится.")) return;
  try {
    await api(`/hotels/${id}/checkout`, { method: "POST" });
    toast("Участник выселен", "success");
    renderSection("hotels");
  } catch (e) { toast(e.message, "error"); }
}

function openHotelModal(confs) {
  const form = el("form", { class: "form" }, [
    el("label", {}, ["Конференция", (() => {
      const sel = el("select", { name: "conference_id", required: true });
      confs.forEach((c) => sel.appendChild(el("option", { value: c.id }, [c.title])));
      return sel;
    })()]),
    el("label", {}, ["Дата заезда", el("input", { type: "date", name: "check_in", required: true })]),
    el("label", {}, ["Дата выезда", el("input", { type: "date", name: "check_out", required: true })]),
    el("div", { class: "actions" }, [
      el("button", { type: "submit", class: "btn primary" }, ["Отправить заявку"]),
      el("button", { type: "button", class: "btn ghost", onclick: closeModal }, ["Отмена"]),
    ]),
  ]);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    try {
      await api("/hotels", {
        method: "POST",
        body: {
          conference_id: Number(fd.get("conference_id")),
          check_in: fd.get("check_in"),
          check_out: fd.get("check_out"),
        },
      });
      toast("Заявка отправлена", "success");
      closeModal();
      renderSection("hotels");
    } catch (err) { toast(err.message, "error"); }
  });
  openModal("Заявка на проживание", form);
}

/* ================= РАССЫЛКИ ================= */

async function renderMailings(root) {
  root.appendChild(el("div", { class: "page-head" }, [el("h2", {}, ["Рассылки"])]));

  if (state.user.role === "admin") {
    const confs = await api("/conferences", { auth: false });
    root.appendChild(el("button", { class: "btn primary", style: "margin-bottom:14px", onclick: () => openMailingModal(confs) }, ["+ Новая рассылка"]));
  }

  const list = await api("/mailings/my");
  if (!list.length) {
    root.appendChild(el("div", { class: "empty" }, ["Сообщений нет"]));
    return;
  }

  list.forEach((m) => {
    root.appendChild(el("div", { class: "card", style: "margin-bottom:12px" }, [
      el("h3", {}, [esc(m.subject)]),
      el("div", { class: "meta" }, [
        el("span", {}, [`📅 ${fmtDateTime(m.sent_at)}`]),
        statusBadge(m.status),
      ]),
      el("p", { class: "desc" }, [esc(m.body)]),
    ]));
  });
}

function openMailingModal(confs) {
  const form = el("form", { class: "form" }, [
    el("label", {}, ["Конференция", (() => {
      const sel = el("select", { name: "conference_id", required: true });
      confs.forEach((c) => sel.appendChild(el("option", { value: c.id }, [c.title])));
      return sel;
    })()]),
    el("label", {}, ["ID участника (пусто = всем зарегистрированным)", el("input", { type: "number", name: "participant_id" })]),
    el("label", {}, ["Тема", el("input", { name: "subject", required: true })]),
    el("label", {}, ["Текст", el("textarea", { name: "body", required: true })]),
    el("div", { class: "actions" }, [
      el("button", { type: "submit", class: "btn primary" }, ["Отправить"]),
      el("button", { type: "button", class: "btn ghost", onclick: closeModal }, ["Отмена"]),
    ]),
  ]);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const pid = fd.get("participant_id");
    try {
      await api("/mailings", {
        method: "POST",
        body: {
          conference_id: Number(fd.get("conference_id")),
          participant_id: pid ? Number(pid) : null,
          subject: fd.get("subject"),
          body: fd.get("body"),
        },
      });
      toast("Рассылка отправлена", "success");
      closeModal();
      renderSection("mailings");
    } catch (err) { toast(err.message, "error"); }
  });
  openModal("Новая рассылка", form);
}

/* ================= ОТЧЁТЫ ================= */

async function renderReports(root) {
  const confs = await api("/conferences", { auth: false });
  root.appendChild(el("div", { class: "page-head" }, [el("h2", {}, ["Отчёты по конференциям"])]));

  if (!confs.length) {
    root.appendChild(el("div", { class: "empty" }, ["Нет данных"]));
    return;
  }

  const select = el("select", { style: "max-width:420px;margin-bottom:18px" });
  confs.forEach((c) => select.appendChild(el("option", { value: c.id }, [c.title])));
  root.appendChild(select);

  const container = el("div");
  root.appendChild(container);

  async function load() {
    container.innerHTML = "";
    try {
      const r = await api(`/conferences/${select.value}/report`);
      container.appendChild(el("div", { class: "stats" }, [
        stat("Участников", r.participants_count),
        stat("Докладов всего", r.abstracts_total),
        stat("Утверждено", r.abstracts_approved),
        stat("На рассмотрении", r.abstracts_pending),
        stat("Отклонено", r.abstracts_rejected),
        stat("Оценок", r.ratings_count),
        stat("Средняя оценка", r.average_score ?? "—"),
        stat("Оргвзносы оплачены", r.fees_paid),
        stat("Оргвзносы ожидают", r.fees_pending),
        stat("Сумма оплат, ₽", r.fees_total_amount.toFixed(2)),
        stat("Заявок в гостиницу", r.hotel_requests),
        stat("Приглашений", r.invitations_sent),
        stat("Рассылок", r.mailings_sent),
      ]));
    } catch (e) {
      container.appendChild(el("div", { class: "empty" }, [e.message]));
    }
  }

  select.addEventListener("change", load);
  load();
}

function stat(label, value) {
  return el("div", { class: "stat" }, [
    el("div", { class: "label" }, [label]),
    el("div", { class: "value" }, [String(value)]),
  ]);
}

/* ================= ПРОФИЛЬ ================= */

async function renderProfile(root) {
  root.appendChild(el("div", { class: "page-head" }, [el("h2", {}, ["Профиль и персональные данные"])]));

  const me = await api("/auth/me");

  root.appendChild(el("div", { class: "card" }, [
    el("div", { class: "meta" }, [
      el("span", {}, [`👤 ${esc(me.full_name)}`]),
      el("span", {}, [`✉️ ${esc(me.email)}`]),
      el("span", {}, [`🔑 ${ROLE_LABELS[me.role] || me.role}`]),
    ]),
  ]));

  const nameInput = el("input", { value: me.full_name });
  const form = el("form", { class: "form", style: "max-width:420px;margin-top:18px" }, [
    el("label", {}, ["Изменить ФИО", nameInput]),
    el("button", { type: "submit", class: "btn primary" }, ["Сохранить"]),
  ]);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const updated = await api("/auth/me", { method: "PATCH", body: { full_name: nameInput.value } });
      state.user = updated;
      $("#user-name").textContent = updated.full_name;
      toast("Профиль обновлён", "success");
    } catch (err) { toast(err.message, "error"); }
  });
  root.appendChild(form);

  root.appendChild(el("h3", { style: "margin-top:34px" }, ["Права субъекта ПДн (152-ФЗ)"]));
  root.appendChild(el("div", { class: "actions" }, [
    el("button", { class: "btn ghost", onclick: exportData }, ["📥 Экспортировать мои данные"]),
    el("button", { class: "btn danger", onclick: deleteAccount }, ["🗑 Удалить аккаунт и все данные"]),
  ]));
}

async function exportData() {
  try {
    const data = await api("/auth/me/data");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "my_personal_data.json";
    a.click();
    URL.revokeObjectURL(url);
    toast("Данные выгружены", "success");
  } catch (e) { toast(e.message, "error"); }
}

async function deleteAccount() {
  if (!confirm("Удалить аккаунт и ВСЕ связанные данные? Действие необратимо.")) return;
  try {
    await api("/auth/me", { method: "DELETE" });
    toast("Аккаунт удалён", "success");
    logout(false);
  } catch (e) { toast(e.message, "error"); }
}