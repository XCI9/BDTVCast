import unittest

from update_data import (
    Candidate,
    UpdateError,
    build_people,
    canonical_url,
    merge_incremental_records,
    parse_episode,
    select_incremental_candidates,
    validate_dataset,
)


def corrections():
    return {
        "episode_overrides": {},
        "appearance_overrides": {},
        "person_aliases": {},
        "person_roles": {},
        "group_appearances": {},
        "person_kinds": {},
    }


def html_page(body: str, title: str = "測試回") -> str:
    return f"""<!doctype html><html><body><main>
      <h1>{title}</h1>
      {body}
    </main></body></html>"""


class ParserTests(unittest.TestCase):
    def test_standard_mc_guest_vtr_and_youtube(self):
        html = html_page(
            """
            <h2>日時</h2><p>2026年7月16日(木)22:03頃～</p>
            <h2>出演</h2><p>愛美（戸山香澄 役）、mika（二葉つくし 役）<br>ゲスト出演：湯田雅（ガルパプロデューサー）</p>
            <h2>ゲスト出演</h2><p>千石ユノ</p>
            <h2>VTR出演</h2><p>西本りみ（牛込りみ 役）</p>
            <p><img src="/wordpress/wp-content/uploads/example-cast.png" alt=""></p>
            <h2>配信URL</h2><p><a href="https://youtube.com/live/example">YouTube Live</a></p>
            """
        )
        candidate = Candidate(
            "https://bang-dream.com/news/9999/", "第323回", "2026-07-09", 323
        )
        episode, appearances = parse_episode(candidate, html, corrections())
        self.assertEqual(episode["episode"], 323)
        self.assertEqual(episode["broadcast_at"], "2026-07-16T22:03:00+09:00")
        self.assertEqual(episode["youtube_url"], "https://youtube.com/live/example")
        self.assertEqual(
            episode["image_url"],
            "https://bang-dream.com/wordpress/wp-content/uploads/example-cast.png",
        )
        self.assertEqual(
            {(item["name"], item["appearance_type"]) for item in appearances},
            {
                ("愛美", "regular"),
                ("mika", "regular"),
                ("千石ユノ", "guest"),
                ("西本りみ", "vtr"),
                ("湯田雅", "guest"),
            },
        )
        producer = next(item for item in appearances if item["name"] == "湯田雅")
        self.assertIsNone(producer["role"])
        self.assertEqual(producer["description"], "ガルパプロデューサー")

    def test_cancellation_is_kept_but_not_marked_appeared(self):
        html = html_page(
            """
            <h2>日時</h2><p>2022年3月17日(木)22:00～</p>
            <h2>出演</h2><p>秦佐和子（若宮イヴ役）、紡木吏佐（チュチュ役）</p>
            <p>※出演予定の紡木吏佐さんにつきまして、体調不良のため出演を見送らせていただきます。</p>
            <h2>配信URL</h2>
            """
        )
        candidate = Candidate(
            "https://bang-dream.com/news/1352/", "第110回", "2022-03-10", 110
        )
        _, appearances = parse_episode(candidate, html, corrections())
        status = {item["name"]: item["status"] for item in appearances}
        self.assertEqual(status["秦佐和子"], "appeared")
        self.assertEqual(status["紡木吏佐"], "cancelled")

    def test_multiple_and_reworded_cancellations_are_detected(self):
        html = html_page(
            """
            <h2>日時</h2><p>2025年10月16日(木)22:03～</p>
            <h2>出演</h2><p>愛美（戸山香澄役）</p>
            <p>※出演予定の小原莉子さん、倉知玲鳳さんにつきまして、体調不良のため出演を見送りとさせていただきます。</p>
            <p>※出演を予定されていました林鼓子さんにつきまして、体調不良のため出演を見送りとさせていただきます。</p>
            <p>何卒ご理解・ご了承の程、よろしくお願い申し上げます。</p>
            <h2>配信URL</h2>
            """
        )
        candidate = Candidate(
            "https://bang-dream.com/news/9998/", "第285回", "2025-10-09", 285
        )
        _, appearances = parse_episode(candidate, html, corrections())
        status = {item["name"]: item["status"] for item in appearances}
        self.assertEqual(status["愛美"], "appeared")
        self.assertEqual(status["小原莉子"], "cancelled")
        self.assertEqual(status["倉知玲鳳"], "cancelled")
        self.assertEqual(status["林鼓子"], "cancelled")
        self.assertNotIn("何卒ご理解の程", status)

    def test_episode_and_datetime_overrides(self):
        html = html_page(
            "<h2>出演キャスト</h2><p>伊藤彩沙（市ヶ谷有咲役）</p>",
            "「バンドリ！TV LIVE 2020」放送決定！",
        )
        url = canonical_url("https://bang-dream.com/news/739")
        config = corrections()
        config["episode_overrides"][url] = {
            "episode": 1,
            "broadcast_at": "2020-01-23T21:30:00+09:00",
            "note": "初回",
        }
        candidate = Candidate(url, "放送決定", "2019-12-12", 1)
        episode, appearances = parse_episode(candidate, html, config)
        self.assertEqual(episode["episode"], 1)
        self.assertEqual(episode["broadcast_at"], "2020-01-23T21:30:00+09:00")
        self.assertEqual(appearances[0]["name"], "伊藤彩沙")

    def test_group_appearance_expands_to_members(self):
        html = html_page(
            """
            <h2>日時</h2><p>2026年7月2日(木)22:03～</p>
            <h2>出演</h2><p>夢限大みゅーたいぷ</p>
            """
        )
        config = corrections()
        config["group_appearances"]["夢限大みゅーたいぷ"] = [
            "仲町あられ",
            "千石ユノ",
            "宮永ののか",
            "峰月律",
            "藤都子",
        ]
        candidate = Candidate(
            "https://bang-dream.com/news/2356/", "第321回", "2026-06-26", 321
        )
        _, appearances = parse_episode(candidate, html, config)
        self.assertEqual(
            {item["name"] for item in appearances},
            {"仲町あられ", "千石ユノ", "宮永ののか", "峰月律", "藤都子"},
        )


class DatasetTests(unittest.TestCase):
    def test_incremental_selection_refreshes_latest_two_and_all_new_episodes(self):
        existing = [
            Candidate(f"https://example/{number}/", f"Episode {number}", "2026-01-01", number)
            for number in range(1, 4)
        ]
        discovered = [
            Candidate(f"https://example/{number}/", f"Episode {number}", "2026-02-01", number)
            for number in range(2, 7)
        ]

        selected = select_incremental_candidates(existing, discovered)

        self.assertEqual([candidate.episode for candidate in selected], [4, 5, 6])

    def test_incremental_selection_refreshes_two_when_there_is_no_new_episode(self):
        existing = [
            Candidate(f"https://example/{number}/", f"Episode {number}", "2026-01-01", number)
            for number in range(1, 5)
        ]

        selected = select_incremental_candidates(existing, existing[-2:])

        self.assertEqual([candidate.episode for candidate in selected], [3, 4])

    def test_incremental_merge_keeps_old_records_and_replaces_refreshed_episode(self):
        existing = {
            "episodes": [
                {"episode": 1, "title": "old one"},
                {"episode": 2, "title": "old two"},
            ],
            "appearances": [
                {"episode": 1, "id": "old-1"},
                {"episode": 2, "id": "old-2"},
            ],
        }
        refreshed_episodes = [
            {"episode": 2, "title": "new two"},
            {"episode": 3, "title": "new three"},
        ]
        refreshed_appearances = [
            {"episode": 2, "id": "new-2"},
            {"episode": 3, "id": "new-3"},
        ]

        episodes, appearances = merge_incremental_records(
            existing, refreshed_episodes, refreshed_appearances
        )

        self.assertEqual([episode["title"] for episode in episodes], ["old one", "new two", "new three"])
        self.assertEqual([appearance["id"] for appearance in appearances], ["old-1", "new-2", "new-3"])

    def test_validation_accepts_contiguous_data_and_people_classification(self):
        episodes = [
            {
                "episode": 1,
                "broadcast_at": "2020-01-23T21:30:00+09:00",
                "announcement_url": "https://example/1",
            },
            {
                "episode": 2,
                "broadcast_at": "2020-01-30T21:30:00+09:00",
                "announcement_url": "https://example/2",
            },
        ]
        appearances = [
            {
                "episode": 1,
                "name": "愛美",
                "display_name": "愛美",
                "role": "戸山香澄",
                "appearance_type": "regular",
                "status": "appeared",
            },
            {
                "episode": 2,
                "name": "千石ユノ",
                "display_name": "千石ユノ",
                "role": None,
                "appearance_type": "guest",
                "status": "appeared",
            },
        ]
        validate_dataset(episodes, appearances)
        people = build_people(appearances, corrections())
        kinds = {person["name"]: person["kind"] for person in people}
        self.assertEqual(kinds, {"愛美": "voice_actor", "千石ユノ": "other"})

    def test_person_kind_overrides_classify_vtubers_as_voice_actors(self):
        appearances = [
            {
                "episode": 1,
                "name": "千石ユノ",
                "display_name": "千石ユノ",
                "role": None,
                "appearance_type": "regular",
                "status": "appeared",
            }
        ]
        config = corrections()
        config["person_kinds"]["千石ユノ"] = "voice_actor"
        people = build_people(appearances, config)
        self.assertEqual(people[0]["kind"], "voice_actor")

    def test_validation_rejects_missing_episode(self):
        episodes = [
            {"episode": 1, "broadcast_at": "2020-01-23T21:30:00+09:00"},
            {"episode": 3, "broadcast_at": "2020-02-06T21:30:00+09:00"},
        ]
        with self.assertRaises(UpdateError):
            validate_dataset(episodes, [])


if __name__ == "__main__":
    unittest.main()
