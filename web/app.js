(function () {
  "use strict";

  const data = window.TV_LIVE_DATA;
  const core = window.DashboardCore;
  const $ = (selector) => document.querySelector(selector);
  const collator = new Intl.Collator(["ja", "zh-Hant"], { sensitivity: "base" });
  const peopleMap = new Map((data?.people || []).map((person) => [person.id, person]));
  let setEpisodeByNumber = null;
  const state = {
    query: "",
    kind: "voice_actor",
    rows: [],
    tableSort: { key: "days", dir: "desc" },
    timelineSort: { key: "days", dir: "desc" },
  };

  const typeLabels = {
    regular: "一般出演",
    mc: "MC",
    guest: "嘉賓",
    vtr: "一般出演",
    remote: "遠端出演",
  };

  const groupOrder = [
    "Poppin'Party",
    "Afterglow",
    "Pastel*Palettes",
    "Roselia",
    "Hello, Happy World!",
    "Morfonica",
    "RAISE A SUILEN",
    "MyGO!!!!!",
    "Ave Mujica",
    "夢限大みゅーたいぷ",
    "其他",
  ];

  const roleGroups = new Map(Object.entries({
    "戸山香澄": "Poppin'Party",
    "花園たえ": "Poppin'Party",
    "牛込りみ": "Poppin'Party",
    "山吹沙綾": "Poppin'Party",
    "市ヶ谷有咲": "Poppin'Party",
    "美竹蘭": "Afterglow",
    "青葉モカ": "Afterglow",
    "上原ひまり": "Afterglow",
    "宇田川巴": "Afterglow",
    "羽沢つぐみ": "Afterglow",
    "丸山彩": "Pastel*Palettes",
    "氷川日菜": "Pastel*Palettes",
    "白鷺千聖": "Pastel*Palettes",
    "大和麻弥": "Pastel*Palettes",
    "若宮イヴ": "Pastel*Palettes",
    "湊友希那": "Roselia",
    "氷川紗夜": "Roselia",
    "今井リサ": "Roselia",
    "宇田川あこ": "Roselia",
    "白金燐子": "Roselia",
    "弦巻こころ": "Hello, Happy World!",
    "瀬田薫": "Hello, Happy World!",
    "北沢はぐみ": "Hello, Happy World!",
    "松原花音": "Hello, Happy World!",
    "奥沢美咲": "Hello, Happy World!",
    "ミッシェル": "Hello, Happy World!",
    "倉田ましろ": "Morfonica",
    "桐ヶ谷透子": "Morfonica",
    "広町七深": "Morfonica",
    "二葉つくし": "Morfonica",
    "八潮瑠唯": "Morfonica",
    "レイヤ": "RAISE A SUILEN",
    "ロック": "RAISE A SUILEN",
    "朝日六花": "RAISE A SUILEN",
    "マスキング": "RAISE A SUILEN",
    "パレオ": "RAISE A SUILEN",
    "チュチュ": "RAISE A SUILEN",
    "高松燈": "MyGO!!!!!",
    "千早愛音": "MyGO!!!!!",
    "要楽奈": "MyGO!!!!!",
    "長崎そよ": "MyGO!!!!!",
    "椎名立希": "MyGO!!!!!",
    "三角初華": "Ave Mujica",
    "若葉睦": "Ave Mujica",
    "八幡海鈴": "Ave Mujica",
    "祐天寺にゃむ": "Ave Mujica",
    "豊川祥子": "Ave Mujica",
    "ドロリス": "Ave Mujica",
    "モーティス": "Ave Mujica",
    "ティモリス": "Ave Mujica",
    "アモーリス": "Ave Mujica",
    "オブリビオニス": "Ave Mujica",
  }));

  const personGroups = new Map(Object.entries({
    "仲町あられ": "夢限大みゅーたいぷ",
    "千石ユノ": "夢限大みゅーたいぷ",
    "宮永ののか": "夢限大みゅーたいぷ",
    "峰月律": "夢限大みゅーたいぷ",
    "藤都子": "夢限大みゅーたいぷ",
  }));

  const bandColors = new Map(Object.entries({
    "Poppin'Party": "#FF3B72",
    Afterglow: "#EE0022",
    "Pastel*Palettes": "#FF88BB",
    Roselia: "#3344AA",
    "Hello, Happy World!": "#FFDD00",
    Morfonica: "#00ABFF",
    "RAISE A SUILEN": "#39C9C5",
    "MyGO!!!!!": "#0B88BB",
    "Ave Mujica": "#881144",
    "夢限大みゅーたいぷ": "#FF7788",
  }));

  const characterColors = new Map(Object.entries({
    戸山香澄: "#FF5522",
    户山香澄: "#FF5522",
    花園たえ: "#0077DD",
    牛込りみ: "#FF55BB",
    山吹沙綾: "#FFCC11",
    "市ヶ谷有咲": "#AA66DD",
    美竹蘭: "#EE0022",
    青葉モカ: "#00CCAA",
    上原ひまり: "#FF9999",
    宇田川巴: "#BB0033",
    羽沢つぐみ: "#FFEE88",
    丸山彩: "#FF88BB",
    氷川日菜: "#55DDEE",
    白鷺千聖: "#FFEEAA",
    大和麻弥: "#99DD88",
    若宮イヴ: "#DDBBFF",
    湊友希那: "#881188",
    氷川紗夜: "#00AABB",
    今井リサ: "#DD2200",
    宇田川あこ: "#DD0088",
    白金燐子: "#BBBBBB",
    弦巻こころ: "#FFEE22",
    瀬田薫: "#AA33CC",
    北沢はぐみ: "#FF9922",
    松原花音: "#44DDFF",
    ミッシェル: "#006699",
    奥沢美咲: "#006699",
    倉田ましろ: "#6677CC",
    "桐ヶ谷透子": "#EE6666",
    広町七深: "#EE7744",
    二葉つくし: "#EE7788",
    八潮瑠唯: "#669988",
    レイヤ: "#CC0000",
    和奏レイ: "#CC0000",
    ロック: "#AAEE22",
    朝日六花: "#AAEE22",
    マスキング: "#EEBB44",
    佐藤ますき: "#EEBB44",
    パレオ: "#FF99BB",
    鳰原令王那: "#FF99BB",
    チュチュ: "#00BBFF",
    珠手ちゆ: "#00BBFF",
    高松燈: "#77BBDD",
    千早愛音: "#FF8899",
    要楽奈: "#77DD77",
    長崎そよ: "#FFDD88",
    椎名立希: "#7777AA",
    三角初華: "#BB9955",
    ドロリス: "#BB9955",
    若葉睦: "#779977",
    モーティス: "#779977",
    八幡海鈴: "#335566",
    ティモリス: "#335566",
    祐天寺にゃむ: "#AA4477",
    アモーリス: "#AA4477",
    豊川祥子: "#7799CC",
    オブリビオニス: "#7799CC",
  }));

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatDate(value, withTime) {
    const options = { year: "numeric", month: "2-digit", day: "2-digit" };
    if (withTime) Object.assign(options, { hour: "2-digit", minute: "2-digit" });
    return new Intl.DateTimeFormat("zh-TW", options).format(new Date(value));
  }

  function splitRoles(person) {
    return (person.roles || []).flatMap((role) => role.split(/[／/]/)).filter(Boolean);
  }

  function cssColorVar(color) {
    return /^#[0-9a-f]{6}$/i.test(color || "") ? ` style="--label-color:${color}"` : "";
  }

  function colorKey(label) {
    return String(label || "").replace(/\s+/g, "");
  }

  function bandLabel(group, extraClass) {
    const color = bandColors.get(group);
    const className = ["band-label", extraClass].filter(Boolean).join(" ");
    return `<span class="${className}"${cssColorVar(color)}>${escapeHtml(group)}</span>`;
  }

  function characterLabel(label) {
    const color = characterColors.get(colorKey(label));
    const className = color ? "character-label character-label--colored" : "character-label";
    return `<span class="${className}"${cssColorVar(color)}>${escapeHtml(label)}</span>`;
  }

  function roleLabelsHtml(value, className) {
    const parts = String(value || "").split(/[／/]/).filter(Boolean);
    if (!parts.length) return "";
    return `<span class="${className}">${parts.map(characterLabel).join(`<span class="label-separator">／</span>`)}</span>`;
  }

  function groupForPerson(person) {
    if (personGroups.has(person.name)) return personGroups.get(person.name);
    const groups = splitRoles(person)
      .map((role) => roleGroups.get(role))
      .filter(Boolean)
      .sort((a, b) => groupOrder.indexOf(a) - groupOrder.indexOf(b));
    return groups[0] || "其他";
  }

  function groupIndex(person) {
    const index = groupOrder.indexOf(groupForPerson(person));
    return index === -1 ? groupOrder.length : index;
  }

  function personLabels(person) {
    if ((person.roles || []).length) return person.roles.join("／");
    return (person.descriptions || []).join("／");
  }

  function optionalText(tag, className, value) {
    return value ? `<${tag} class="${className}">${escapeHtml(value)}</${tag}>` : "";
  }

  function episodeButton(episodeNumber, label) {
    return `<button class="episode-link-button" data-episode-nav="${Number(episodeNumber)}" type="button">${escapeHtml(label || `第 ${episodeNumber} 回`)}</button>`;
  }

  function episodeTitle(episodeNumber) {
    return `第 ${Number(episodeNumber)} 回`;
  }

  function personButton(person, extraClass) {
    const className = ["person-button", extraClass].filter(Boolean).join(" ");
    return `<button class="${className}" data-person-id="${escapeHtml(person.id)}" type="button">${escapeHtml(person.display_name)}</button>`;
  }

  function personForAppearance(item) {
    return peopleMap.get(item.person_id) || null;
  }

  function appearancePersonButton(item, extraClass) {
    const person = personForAppearance(item);
    if (!person) return escapeHtml(item.display_name);
    return personButton(person, extraClass);
  }

  function episodeImage(episode, className) {
    if (!episode.image_url) return "";
    return `<img class="${className}" src="${escapeHtml(episode.image_url)}" alt="第 ${episode.episode} 回出演者圖片" loading="lazy" referrerpolicy="no-referrer" />`;
  }

  function typeBadge(item) {
    const cancelled = item.status === "cancelled";
    const label = cancelled ? "取消出演" : (typeLabels[item.appearance_type] || item.appearance_type);
    const extraClass = cancelled ? " type-badge--cancelled" : "";
    return `<span class="type-badge${extraClass}">${escapeHtml(label)}</span>`;
  }

  function renderSummary() {
    const now = new Date();
    const completed = core.completedEpisodes(data, now);
    const latest = completed[0];
    const cards = [
      ["最近已播出", latest ? episodeButton(latest.episode) : "—", latest ? formatDate(latest.broadcast_at) : ""],
      ["資料更新", formatDate(data.metadata.generated_at, true), "官方網站公告"],
    ];
    $("#summaryCards").innerHTML = cards.map(([label, value, sub]) => `
      <div class="summary-card">
        <span class="summary-card__label">${escapeHtml(label)}</span>
        <strong class="summary-card__value">${value}</strong>
        <span class="summary-card__sub">${escapeHtml(sub)}</span>
      </div>`).join("");
  }

  function positionPercent(value, min, max) {
    if (!value || max <= min) return 2;
    return Math.max(2, Math.min(98, ((new Date(value).getTime() - min) / (max - min)) * 96 + 2));
  }

  function yearMarkers(min, max) {
    const startYear = new Date(min).getFullYear() + 1;
    const endYear = new Date(max).getFullYear();
    const markers = [];
    for (let year = startYear; year <= endYear; year += 1) {
      const value = new Date(year, 0, 1).getTime();
      if (value <= min || value >= max) continue;
      markers.push({
        year,
        position: positionPercent(value, min, max),
      });
    }
    return markers;
  }

  function timelineItemsForRow(row, now) {
    const current = now.getTime();
    const futureItems = data.appearances
      .filter((item) =>
        item.person_id === row.person.id &&
        item.status !== "cancelled" &&
        new Date(item.broadcast_at).getTime() > current
      )
      .map((item) => ({ ...item, isUpcoming: true }));
    return [
      ...row.history.map((item) => ({ ...item, isUpcoming: false })),
      ...futureItems,
    ].sort((a, b) =>
      new Date(a.broadcast_at).getTime() - new Date(b.broadcast_at).getTime() ||
      Number(a.episode) - Number(b.episode)
    );
  }

  function compareNumberRows(a, b, selector, dir) {
    const left = selector(a);
    const right = selector(b);
    if (left === null && right === null) return collator.compare(a.person.name, b.person.name);
    if (left === null) return 1;
    if (right === null) return -1;
    const result = left - right;
    return result === 0
      ? collator.compare(a.person.name, b.person.name)
      : dir === "asc" ? result : -result;
  }

  function compareGroupRows(a, b, dir) {
    const result = groupIndex(a.person) - groupIndex(b.person);
    if (result !== 0) return dir === "asc" ? result : -result;
    return collator.compare(a.person.name, b.person.name);
  }

  function sortRows(rows, sort) {
    return [...rows].sort((a, b) => {
      if (sort.key === "group") return compareGroupRows(a, b, sort.dir);
      if (sort.key === "count") return compareNumberRows(a, b, (row) => row.count, sort.dir);
      return compareNumberRows(a, b, (row) => row.daysSince, sort.dir);
    });
  }

  function defaultDirection(key) {
    return key === "group" ? "asc" : "desc";
  }

  function renderSortIndicators() {
    document.querySelectorAll("[data-sort-indicator]").forEach((node) => {
      const key = node.dataset.sortIndicator;
      node.textContent = key === state.tableSort.key ? (state.tableSort.dir === "asc" ? "↑" : "↓") : "";
    });
    $("#timelineSortSelect").value = state.timelineSort.key;
    $("#timelineDirection").textContent = state.timelineSort.dir === "asc" ? "↑" : "↓";
  }

  function renderTable(rows) {
    const sortedRows = sortRows(rows, state.tableSort);
    $("#peopleTable").innerHTML = sortedRows.map((row) => `
      <tr>
        <td>${personButton(row.person)}${bandLabel(groupForPerson(row.person), "group-label")}${roleLabelsHtml(personLabels(row.person), "roles")}</td>
        <td>${row.last ? `<span class="date-main">${formatDate(row.last.broadcast_at)}</span><span class="date-sub">${episodeButton(row.last.episode)} · ${escapeHtml(typeLabels[row.last.appearance_type] || row.last.appearance_type)}</span>` : "—"}</td>
        <td>${row.daysSince === null ? "—" : `<span class="days-pill">${row.daysSince} 天</span>`}</td>
        <td>${row.count} 回</td>
      </tr>`).join("");
  }

  function renderTimeline(rows) {
    const sortedRows = sortRows(rows, state.timelineSort);
    const now = new Date();
    const allDates = data.episodes.map((episode) => new Date(episode.broadcast_at).getTime());
    const min = Math.min(...allDates);
    const max = Math.max(now.getTime(), ...allDates);
    const markers = yearMarkers(min, max);
    const timelineItems = new Map(sortedRows.map((row) => [row.person.id, timelineItemsForRow(row, now)]));
    $("#fullTimeline").innerHTML = sortedRows.length ? sortedRows.map((row) => `
      <div class="timeline-row">
        <div class="plot-name timeline-name">
          ${personButton(row.person)}
          <span class="timeline-meta">${bandLabel(groupForPerson(row.person))} · ${row.count} 回</span>
        </div>
        <div class="timeline-dots">
          ${markers.map((marker) => `<span class="timeline-year-line" style="left:${marker.position}%" title="${marker.year}"></span>`).join("")}
          ${(timelineItems.get(row.person.id) || []).map((item) => {
            const pos = positionPercent(item.broadcast_at, min, max);
            const label = `${episodeTitle(item.episode)} · ${formatDate(item.broadcast_at)}`;
            const lastClass = row.last && item.id === row.last.id ? " timeline-dot--last" : "";
            const upcomingClass = item.isUpcoming ? " timeline-dot--upcoming" : "";
            return `<button class="timeline-dot${lastClass}${upcomingClass}" data-episode-nav="${Number(item.episode)}" data-tooltip="${escapeHtml(label)}" style="left:${pos}%" aria-label="${escapeHtml(label)}" type="button"></button>`;
          }).join("")}
        </div>
        <div class="timeline-last">
          ${row.last ? `<strong>${row.daysSince} 天</strong><span>${episodeButton(row.last.episode)}</span>` : "<span>尚無紀錄</span>"}
        </div>
      </div>`).join("") : `<div class="empty-state">沒有可顯示的時間軸。</div>`;
  }

  function renderUpcoming() {
    const episodes = core.upcomingEpisodes(data, new Date());
    $("#upcomingList").innerHTML = episodes.length ? episodes.map((episode) => {
      const people = core.appearancesForEpisode(data, episode.episode).filter((item) => item.status !== "cancelled");
      return `<article class="upcoming-card">
        <div class="cast-layout cast-layout--upcoming">
          ${episodeImage(episode, "episode-image episode-image--upcoming")}
          <div class="cast-layout__content">
            <h3>${episodeButton(episode.episode)}</h3>
            <p class="upcoming-card__date">${formatDate(episode.broadcast_at, true)}</p>
            <div class="chip-list">${people.map((item) => `<span class="chip">${appearancePersonButton(item)}</span>`).join("")}</div>
          </div>
        </div>
      </article>`;
    }).join("") : `<div class="empty-state">目前沒有尚未播出的公告。</div>`;
  }

  function renderEpisode(episodeNumber) {
    const episode = data.episodes.find((item) => item.episode === Number(episodeNumber));
    if (!episode) return;
    const appearances = core.appearancesForEpisode(data, episode.episode);
    $("#episodeDetail").innerHTML = `
      <div class="episode-meta">
        <h3>${escapeHtml(episodeTitle(episode.episode))}</h3>
        <p>${formatDate(episode.broadcast_at, true)}</p>
      </div>
      ${episode.correction_note ? `<p class="section-note">資料修正：${escapeHtml(episode.correction_note)}</p>` : ""}
      <div class="episode-links">
        <a class="link-button" href="${escapeHtml(episode.announcement_url)}" target="_blank" rel="noreferrer">官方公告 ↗</a>
        ${episode.youtube_url ? `<a class="link-button" href="${escapeHtml(episode.youtube_url)}" target="_blank" rel="noreferrer">YouTube ↗</a>` : ""}
      </div>
      <div class="cast-layout cast-layout--detail">
        ${episodeImage(episode, "episode-image episode-image--detail")}
        <div class="appearance-list">
          ${appearances.map((item) => `<div class="appearance-item${item.status === "cancelled" ? " appearance-item--cancelled" : ""}">
            <span class="appearance-item__name">${appearancePersonButton(item)}</span>
            ${roleLabelsHtml(item.role || item.description, "appearance-item__role")}
            ${typeBadge(item)}
          </div>`).join("")}
        </div>
      </div>`;
  }

  function setupEpisodeSelector() {
    const select = $("#episodeSelect");
    select.innerHTML = [...data.episodes].reverse().map((episode) =>
      `<option value="${episode.episode}">第 ${episode.episode} 回 · ${formatDate(episode.broadcast_at)}</option>`
    ).join("");
    const completed = core.completedEpisodes(data, new Date());
    const numbers = data.episodes.map((episode) => episode.episode);
    const minEpisode = Math.min(...numbers);
    const maxEpisode = Math.max(...numbers);
    const updateEpisodeNav = () => {
      const value = Number(select.value);
      $("#episodePrev").disabled = value <= minEpisode;
      $("#episodeNext").disabled = value >= maxEpisode;
    };
    const setEpisode = (episodeNumber) => {
      const value = Math.max(minEpisode, Math.min(maxEpisode, Number(episodeNumber)));
      select.value = String(value);
      renderEpisode(value);
      updateEpisodeNav();
    };
    setEpisodeByNumber = setEpisode;
    select.value = String(completed[0]?.episode || data.metadata.latest_episode);
    renderEpisode(select.value);
    updateEpisodeNav();
    select.addEventListener("change", () => setEpisode(select.value));
    $("#episodePrev").addEventListener("click", () => setEpisode(Number(select.value) - 1));
    $("#episodeNext").addEventListener("click", () => setEpisode(Number(select.value) + 1));
  }

  function showPerson(personId) {
    const person = data.people.find((item) => item.id === personId);
    if (!person) return;
    const history = data.appearances
      .filter((item) => item.person_id === personId)
      .sort((a, b) => new Date(b.broadcast_at) - new Date(a.broadcast_at));
    const labels = personLabels(person);
    $("#personDetail").innerHTML = `<div class="person-detail">
      <p class="section-kicker">APPEARANCE HISTORY</p>
      <h2>${escapeHtml(person.display_name)}</h2>
      <p class="person-detail__roles">${bandLabel(groupForPerson(person))}${labels ? ` · ${roleLabelsHtml(labels, "person-detail__character-roles")}` : ""}</p>
      <div class="history-list">
        ${history.map((item) => `<div class="history-item">
          <div class="history-item__episode">${episodeButton(item.episode)}</div>
          <div class="history-item__date">${formatDate(item.broadcast_at)}</div>
          ${typeBadge(item)}
        </div>`).join("")}
      </div>
    </div>`;
    $("#personDialog").showModal();
  }

  function refresh() {
    state.rows = core.summarizePeople(data, {
      query: state.query,
      kind: state.kind,
      now: new Date(),
    });
    $("#resultCount").textContent = `${state.rows.length} 位`;
    renderSortIndicators();
    renderTable(state.rows);
    renderTimeline(state.rows);
  }

  function toggleSort(target, key) {
    if (target.key === key) {
      target.dir = target.dir === "asc" ? "desc" : "asc";
    } else {
      target.key = key;
      target.dir = defaultDirection(key);
    }
  }

  function setPanelCollapsed(panel, button, collapsed) {
    panel.classList.toggle("is-collapsed", collapsed);
    button.setAttribute("aria-expanded", String(!collapsed));
    button.setAttribute("aria-label", collapsed ? "展開此區塊" : "收合此區塊");
    button.setAttribute("title", collapsed ? "展開" : "收合");
    button.querySelector("[aria-hidden]").textContent = collapsed ? "+" : "−";
  }

  function setupPanelToggles() {
    document.querySelectorAll("[data-panel-toggle]").forEach((button) => {
      const panel = button.closest(".panel");
      if (!panel) return;
      setPanelCollapsed(panel, button, false);
      button.addEventListener("click", () => {
        setPanelCollapsed(panel, button, !panel.classList.contains("is-collapsed"));
      });
    });
  }

  function setupEvents() {
    const filterToggle = $("#filterToggle");
    const filterPanel = $("#filterPanel");
    filterToggle.addEventListener("click", () => {
      const willOpen = filterPanel.hidden;
      filterPanel.hidden = !willOpen;
      filterToggle.setAttribute("aria-expanded", String(willOpen));
    });
    document.addEventListener("click", (event) => {
      if (event.target.closest(".filter-widget")) return;
      filterPanel.hidden = true;
      filterToggle.setAttribute("aria-expanded", "false");
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      filterPanel.hidden = true;
      filterToggle.setAttribute("aria-expanded", "false");
    });
    $("#searchInput").addEventListener("input", (event) => { state.query = event.target.value; refresh(); });
    $("#kindSelect").addEventListener("change", (event) => { state.kind = event.target.value; refresh(); });
    document.querySelectorAll("[data-table-sort]").forEach((button) => {
      button.addEventListener("click", () => {
        toggleSort(state.tableSort, button.dataset.tableSort);
        refresh();
      });
    });
    $("#timelineSortSelect").addEventListener("change", (event) => {
      state.timelineSort.key = event.target.value;
      state.timelineSort.dir = defaultDirection(state.timelineSort.key);
      refresh();
    });
    $("#timelineDirection").addEventListener("click", () => {
      state.timelineSort.dir = state.timelineSort.dir === "asc" ? "desc" : "asc";
      refresh();
    });
    document.addEventListener("click", (event) => {
      const episodeButtonNode = event.target.closest("[data-episode-nav]");
      if (episodeButtonNode) {
        setEpisodeByNumber?.(Number(episodeButtonNode.dataset.episodeNav));
        if ($("#personDialog")?.open) $("#personDialog").close();
        $("#episodesTitle").scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      const button = event.target.closest("[data-person-id]");
      if (button) showPerson(button.dataset.personId);
    });
    $("#closeDialog").addEventListener("click", () => $("#personDialog").close());
    $("#personDialog").addEventListener("click", (event) => {
      if (event.target === $("#personDialog")) $("#personDialog").close();
    });
  }

  function init() {
    if (!data || !core) throw new Error("找不到產生的資料。請先在專案根目錄執行 python update_data.py。 ");
    renderSummary();
    renderUpcoming();
    setupEpisodeSelector();
    setupPanelToggles();
    setupEvents();
    refresh();
    $("#dataProvenance").innerHTML = `資料產生於 ${escapeHtml(formatDate(data.metadata.generated_at, true))} · <a href="${escapeHtml(data.metadata.source)}" target="_blank" rel="noreferrer">BanG Dream! 官方網站</a>`;
  }

  try {
    init();
  } catch (error) {
    const box = $("#fatalError");
    box.hidden = false;
    box.textContent = `無法載入儀表板：${error.message}`;
    console.error(error);
  }
})();
