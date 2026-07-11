const assert = require("node:assert/strict");
const core = require("../web/dashboard-core.js");

const data = {
  people: [
    { id: "a", name: "愛美", display_name: "愛美", kind: "voice_actor", roles: ["戸山香澄"] },
    { id: "b", name: "西本りみ", display_name: "西本りみ", kind: "voice_actor", roles: ["牛込りみ"] },
  ],
  episodes: [
    { episode: 1, broadcast_at: "2026-01-01T22:00:00+09:00" },
    { episode: 2, broadcast_at: "2026-02-01T22:00:00+09:00" },
    { episode: 3, broadcast_at: "2026-03-01T22:00:00+09:00" },
    { episode: 4, broadcast_at: "2026-12-01T22:00:00+09:00" },
  ],
  appearances: [
    { person_id: "a", episode: 1, broadcast_at: "2026-01-01T22:00:00+09:00", appearance_type: "regular", status: "appeared" },
    { person_id: "a", episode: 2, broadcast_at: "2026-02-01T22:00:00+09:00", appearance_type: "vtr", status: "appeared" },
    { person_id: "a", episode: 3, broadcast_at: "2026-03-01T22:00:00+09:00", appearance_type: "regular", status: "cancelled" },
    { person_id: "a", episode: 4, broadcast_at: "2026-12-01T22:00:00+09:00", appearance_type: "regular", status: "appeared" },
    { person_id: "b", episode: 2, broadcast_at: "2026-02-01T22:00:00+09:00", appearance_type: "regular", status: "appeared" },
  ],
};

const now = new Date("2026-07-12T12:00:00+08:00");
const actual = core.summarizePeople(data, { now, kind: "voice_actor", mode: "actual" });
assert.equal(actual.find((row) => row.person.id === "a").last.episode, 2, "VTR 應計入上次出場，取消與未來出演不應覆寫");
assert.equal(actual.find((row) => row.person.id === "b").last.episode, 2);

const withVtr = core.summarizePeople(data, { now, kind: "voice_actor", mode: "all" });
assert.equal(withVtr.find((row) => row.person.id === "a").last.episode, 2, "相容模式仍應計入 VTR");

assert.deepEqual(core.upcomingEpisodes(data, now).map((item) => item.episode), [4]);
assert.deepEqual(core.completedEpisodes(data, now).map((item) => item.episode), [3, 2, 1]);
console.log("dashboard core tests passed");
