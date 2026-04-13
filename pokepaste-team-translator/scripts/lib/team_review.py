from __future__ import annotations

from scripts.lib.translation_assets import DictionaryBundle


def review_translation(
    raw_team: dict,
    team_zh: dict,
    validation_report: dict,
    bundle: DictionaryBundle,
) -> dict:
    alias_suggestions = []
    ambiguous_findings = []
    for issue in validation_report.get("issues", []):
        if issue.get("code") != "missing_translation":
            continue
        suggestion = bundle.suggest_alias(issue["term"], issue["field"])
        if suggestion:
            alias_suggestions.append(suggestion)
        else:
            ambiguous_findings.append(
                {
                    "field": issue["field"],
                    "term": issue["term"],
                    "member_slot": issue.get("member_slot"),
                    "message": "Translation could not be resolved deterministically.",
                }
            )
    status = "ok"
    if alias_suggestions or ambiguous_findings:
        status = "needs-attention"
    return {
        "status": status,
        "alias_suggestions": alias_suggestions,
        "ambiguous_findings": ambiguous_findings,
    }
