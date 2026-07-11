(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.DashboardCore = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function toDate(value) {
    return value instanceof Date ? value : new Date(value);
  }

  function startOfDay(value) {
    const date = toDate(value);
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  function daysBetween(later, earlier) {
    return Math.max(
      0,
      Math.floor((startOfDay(later).getTime() - startOfDay(earlier).getTime()) / 86400000)
    );
  }

  function isCompleted(appearance, now) {
    return toDate(appearance.broadcast_at).getTime() <= toDate(now).getTime();
  }

  function countsForMode(appearance, mode) {
    if (appearance.status !== "appeared") return false;
    return true;
  }

  function summarizePeople(data, options) {
    const now = toDate(options.now || new Date());
    const kind = options.kind || "voice_actor";
    const query = (options.query || "").trim().toLocaleLowerCase("zh-Hant");
    const peopleById = new Map(data.people.map((person) => [person.id, person]));
    const appearancesByPerson = new Map();

    for (const appearance of data.appearances) {
      if (!appearancesByPerson.has(appearance.person_id)) {
        appearancesByPerson.set(appearance.person_id, []);
      }
      appearancesByPerson.get(appearance.person_id).push(appearance);
    }

    const rows = [];
    for (const [personId, person] of peopleById) {
      if (kind !== "all" && person.kind !== kind) continue;
      const haystack = `${person.display_name} ${person.name} ${(person.roles || []).join(" ")}`
        .toLocaleLowerCase("zh-Hant");
      if (query && !haystack.includes(query)) continue;

      const history = (appearancesByPerson.get(personId) || [])
        .filter((item) => isCompleted(item, now) && countsForMode(item, options.mode))
        .sort((a, b) => toDate(a.broadcast_at) - toDate(b.broadcast_at));
      const last = history.length ? history[history.length - 1] : null;
      rows.push({
        person,
        history,
        last,
        count: history.length,
        daysSince: last ? daysBetween(now, last.broadcast_at) : null,
      });
    }

    rows.sort((a, b) => {
      if (a.daysSince === null) return -1;
      if (b.daysSince === null) return 1;
      return b.daysSince - a.daysSince || a.person.name.localeCompare(b.person.name, "ja");
    });
    return rows;
  }

  function upcomingEpisodes(data, now) {
    const current = toDate(now || new Date()).getTime();
    return data.episodes
      .filter((episode) => toDate(episode.broadcast_at).getTime() > current)
      .sort((a, b) => toDate(a.broadcast_at) - toDate(b.broadcast_at));
  }

  function completedEpisodes(data, now) {
    const current = toDate(now || new Date()).getTime();
    return data.episodes
      .filter((episode) => toDate(episode.broadcast_at).getTime() <= current)
      .sort((a, b) => b.episode - a.episode);
  }

  function appearancesForEpisode(data, episodeNumber) {
    return data.appearances.filter((item) => item.episode === Number(episodeNumber));
  }

  return {
    appearancesForEpisode,
    completedEpisodes,
    countsForMode,
    daysBetween,
    isCompleted,
    summarizePeople,
    upcomingEpisodes,
  };
});
