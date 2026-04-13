import json
import tempfile
import unittest
from pathlib import Path

from scripts.lib.dictionary_builder import build_dictionary_payloads
from scripts.lib.html_rendering import render_share_card_html
from scripts.lib.team_review import review_translation
from scripts.lib.translation_assets import load_assets_config, load_dictionary_bundle
from scripts.lib.translation_pipeline import (
    build_translated_team_artifacts,
    parse_pokepaste_html,
    translate_team,
)
from scripts.lib.translation_validation import validate_translated_team


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "pokepaste"
DICT_DIR = REPO_ROOT / "dict"
IMAGE_ROOT = REPO_ROOT / "temp" / "pokemon-dataset-zh" / "data" / "images"


class TranslationPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_dictionary_bundle(
            dict_dir=DICT_DIR,
            image_root=IMAGE_ROOT,
            image_base_url="https://mewtwo.host/pmc/images/",
        )
        cls.assets_config = {
            "image_source_base_url": "https://mewtwo.host/pmc/images/",
            "templates": {
                "compact-mobile": {
                    "html_template": "assets/templates/compact-mobile.html",
                },
                "pokepaste-like": {
                    "html_template": "assets/templates/pokepaste-like.html",
                },
            },
            "default_template": "compact-mobile",
        }

    def fixture_text(self, name):
        return (FIXTURE_ROOT / name).read_text(encoding="utf-8")

    def test_build_dictionary_payloads_extracts_core_mappings(self):
        payloads = build_dictionary_payloads(
            dataset_root=REPO_ROOT / "temp" / "pokemon-dataset-zh" / "data",
            image_root=IMAGE_ROOT,
            existing_dict_dir=DICT_DIR,
        )

        self.assertEqual(payloads["pokemon"]["Charizard"], "喷火龙")
        self.assertEqual(payloads["pokemon"]["Kingambit"], "仆刀将军")
        self.assertEqual(payloads["moves"]["Heat Wave"], "热风")
        self.assertEqual(payloads["abilities"]["Intimidate"], "威吓")
        self.assertEqual(payloads["items"]["Focus Sash"], "气势披带")
        self.assertEqual(payloads["pokemon-forms"]["Charizard-Mega-Y"], "超级喷火龙Ｙ")
        self.assertEqual(payloads["pokemon-images"]["喷火龙"], "home/0006-喷火龙.png")
        self.assertEqual(payloads["item-images"]["气势披带"], "items/气势披带.png")

    def test_parse_pokepaste_html_extracts_expected_metadata(self):
        raw_team = parse_pokepaste_html(
            self.fixture_text("huyubare.html"),
            "https://pokepast.es/d9260baad4fd55f8",
        )

        self.assertEqual(raw_team["meta"]["author"], "Huyubare")
        self.assertEqual(raw_team["meta"]["team_name"], "Charizard-Y Garchomp Team")
        self.assertEqual(raw_team["meta"]["team_code"], "GRJP9BKHTD")
        self.assertEqual(raw_team["meta"]["format"], "gen9championsvgc2026regma")
        self.assertEqual(len(raw_team["members"]), 6)
        self.assertEqual(raw_team["members"][0]["species"], "Charizard")
        self.assertEqual(raw_team["members"][2]["species"], "Garchomp")
        self.assertEqual(raw_team["members"][4]["species"], "Maushold-Four")
        self.assertEqual(raw_team["members"][4]["gender"], None)
        self.assertEqual(raw_team["members"][0]["moves"][0], "Heat Wave")

    def test_translate_team_adds_chinese_fields_and_image_urls(self):
        raw_team = parse_pokepaste_html(
            self.fixture_text("ub_slow.html"),
            "https://pokepast.es/50c3bdabb5fe8186",
        )

        team_zh = translate_team(raw_team, self.bundle, self.assets_config)

        self.assertEqual(team_zh["meta"]["author"], "UB_SLOW")
        self.assertEqual(team_zh["members"][0]["species_zh"], "炽焰咆哮虎")
        self.assertEqual(team_zh["members"][1]["species_zh"], "耿鬼")
        self.assertEqual(team_zh["members"][5]["species_zh"], "杖尾鳞甲龙")
        self.assertEqual(team_zh["members"][0]["item_zh"], "腰木果")
        self.assertEqual(team_zh["members"][0]["ability_zh"], "威吓")
        self.assertEqual(team_zh["members"][1]["moves_zh"][0], "暗影球")
        self.assertEqual(team_zh["members"][0]["images"]["pokemon"]["status"], "ok")
        self.assertTrue(
            team_zh["members"][0]["images"]["pokemon"]["url"].startswith(
                "https://mewtwo.host/pmc/images/"
            )
        )
        self.assertEqual(team_zh["unresolved_terms"], [])

    def test_validate_translated_team_keeps_structural_findings_separate(self):
        raw_team = parse_pokepaste_html(
            self.fixture_text("gahaku.html"),
            "https://pokepast.es/65b7228ad81523a5",
        )
        team_zh = translate_team(raw_team, self.bundle, self.assets_config)

        report = validate_translated_team(raw_team, team_zh, self.assets_config)

        self.assertEqual(report["status"], "ok")
        self.assertIn("issues", report)
        self.assertEqual(report["issues"], [])
        self.assertNotIn("alias_suggestions", report)

    def test_validate_translated_team_reports_missing_required_fields(self):
        raw_team = {
            "meta": {
                "source_url": "fixture://missing-required",
                "team_name": "Broken Team",
            },
            "members": [{"slot": 1, "moves": []}],
        }
        team_zh = {
            "meta": {
                "source_url": "fixture://missing-required",
                "title": "Broken Team",
                "image_source_base_url": "https://mewtwo.host/pmc/images/",
            },
            "members": [
                {
                    "slot": 1,
                    "species": "Pikachu",
                    "moves_zh": [],
                    "images": {
                        "pokemon": {"status": "ok"},
                        "item": {"status": "missing"},
                    },
                }
            ],
            "unresolved_terms": [],
        }

        report = validate_translated_team(raw_team, team_zh, self.assets_config)

        self.assertEqual(report["status"], "error")
        missing_fields = {
            issue["field"]
            for issue in report["issues"]
            if issue["code"] == "missing_required_field"
        }
        self.assertIn("raw_team.meta.title", missing_fields)
        self.assertIn("raw_team.members[1].species", missing_fields)
        self.assertIn("team_zh.meta.team_name", missing_fields)

    def test_review_translation_emits_deterministic_alias_suggestions(self):
        raw_team = {
            "meta": {"source_url": "fixture://review-case"},
            "members": [{"slot": 1, "species": "Maushold-Four (F)"}],
        }
        team_zh = {
            "meta": {"source_url": "fixture://review-case"},
            "members": [
                {
                    "slot": 1,
                    "species": "Maushold-Four (F)",
                    "species_zh": None,
                }
            ],
            "unresolved_terms": [
                {
                    "field": "species",
                    "term": "Maushold-Four (F)",
                    "member_slot": 1,
                }
            ],
        }
        validation_report = {
            "status": "error",
            "issues": [
                {
                    "code": "missing_translation",
                    "field": "species",
                    "term": "Maushold-Four (F)",
                    "member_slot": 1,
                }
            ],
        }

        review = review_translation(raw_team, team_zh, validation_report, self.bundle)

        self.assertEqual(review["status"], "needs-attention")
        self.assertEqual(len(review["alias_suggestions"]), 1)
        self.assertEqual(
            review["alias_suggestions"][0]["source_term"], "Maushold-Four (F)"
        )
        self.assertEqual(
            review["alias_suggestions"][0]["canonical_term"], "Maushold-Four"
        )
        self.assertEqual(review["alias_suggestions"][0]["translation"], "一家鼠-四只家庭")

    def test_render_share_card_uses_selected_template_and_translated_fields(self):
        raw_team = parse_pokepaste_html(
            self.fixture_text("huyubare.html"),
            "https://pokepast.es/d9260baad4fd55f8",
        )
        team_zh = translate_team(raw_team, self.bundle, self.assets_config)

        html_text = render_share_card_html(
            team_zh,
            self.assets_config,
            template_name="pokepaste-like",
        )

        self.assertIn("Huyubare&#x27;s Charizard-Y Garchomp Team", html_text)
        self.assertIn("GRJP9BKHTD", html_text)
        self.assertIn("喷火龙", html_text)
        self.assertIn("烈咬陆鲨", html_text)
        self.assertIn("https://mewtwo.host/pmc/images/", html_text)
        self.assertIn("data-template=\"pokepaste-like\"", html_text)

    def test_build_translated_team_artifacts_writes_preserved_outputs(self):
        raw_team = parse_pokepaste_html(
            self.fixture_text("gahaku.html"),
            "https://pokepast.es/65b7228ad81523a5",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "gahaku"
            build_translated_team_artifacts(
                raw_team=raw_team,
                bundle=self.bundle,
                assets_config=self.assets_config,
                output_dir=output_dir,
                template_name="compact-mobile",
            )

            expected_files = {
                "team-raw.json",
                "team-zh.json",
                "validation-report.json",
                "review-suggestions.json",
                "share-card.html",
            }
            self.assertEqual(expected_files, {path.name for path in output_dir.iterdir()})

            team_zh = json.loads((output_dir / "team-zh.json").read_text(encoding="utf-8"))
            review = json.loads(
                (output_dir / "review-suggestions.json").read_text(encoding="utf-8")
            )
            rendered_html = (output_dir / "share-card.html").read_text(encoding="utf-8")

            self.assertEqual(team_zh["members"][0]["species_zh"], "来悲粗茶")
            self.assertEqual(team_zh["members"][2]["species_zh"], "花叶蒂-永恒之花")
            self.assertIn(review["status"], {"ok", "needs-attention"})
        self.assertIn("gahaku", rendered_html)

    def test_build_translated_team_artifacts_falls_back_for_unknown_template(self):
        raw_team = parse_pokepaste_html(
            self.fixture_text("huyubare.html"),
            "https://pokepast.es/d9260baad4fd55f8",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "huyubare"
            build_translated_team_artifacts(
                raw_team=raw_team,
                bundle=self.bundle,
                assets_config=self.assets_config,
                output_dir=output_dir,
                template_name="does-not-exist",
            )

            validation_report = json.loads(
                (output_dir / "validation-report.json").read_text(encoding="utf-8")
            )
            rendered_html = (output_dir / "share-card.html").read_text(encoding="utf-8")

            self.assertIn(
                "invalid_template_name",
                {issue["code"] for issue in validation_report["issues"]},
            )
            self.assertIn('data-template="compact-mobile"', rendered_html)


class AssetsConfigTest(unittest.TestCase):
    def test_load_assets_config_reads_template_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "assets.json"
            config_path.write_text(
                json.dumps(
                    {
                        "image_source_base_url": "https://mewtwo.host/pmc/images/",
                        "templates": {
                            "compact-mobile": {
                                "html_template": "assets/templates/compact-mobile.html"
                            }
                        },
                        "default_template": "compact-mobile",
                    }
                ),
                encoding="utf-8",
            )

            loaded = load_assets_config(config_path)

            self.assertEqual(
                loaded["image_source_base_url"], "https://mewtwo.host/pmc/images/"
            )
            self.assertEqual(loaded["default_template"], "compact-mobile")


if __name__ == "__main__":
    unittest.main()
