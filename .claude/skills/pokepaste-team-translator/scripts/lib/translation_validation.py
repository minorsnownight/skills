from __future__ import annotations


def _add_missing_required_issue(
    issues: list[dict],
    field: str,
    member_slot: int | None = None,
) -> None:
    issue = {
        "code": "missing_required_field",
        "field": field,
    }
    if member_slot is not None:
        issue["member_slot"] = member_slot
    issues.append(issue)


def _has_value(mapping: dict, key: str) -> bool:
    return key in mapping and mapping[key] is not None and mapping[key] != ""


def _validate_required_meta_fields(
    issues: list[dict],
    payload: dict,
    prefix: str,
) -> None:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        _add_missing_required_issue(issues, f"{prefix}.meta")
        return
    for key in ("source_url", "title", "team_name"):
        if not _has_value(meta, key):
            _add_missing_required_issue(issues, f"{prefix}.meta.{key}")


def _validate_required_member_fields(
    issues: list[dict],
    payload: dict,
    prefix: str,
    required_fields: tuple[str, ...],
) -> None:
    members = payload.get("members")
    if not isinstance(members, list):
        _add_missing_required_issue(issues, f"{prefix}.members")
        return
    for index, member in enumerate(members, start=1):
        if not isinstance(member, dict):
            _add_missing_required_issue(issues, f"{prefix}.members[{index}]")
            continue
        member_slot = member.get("slot") if isinstance(member.get("slot"), int) else None
        slot_label = member_slot if member_slot is not None else index
        for field in required_fields:
            if not _has_value(member, field):
                _add_missing_required_issue(
                    issues,
                    f"{prefix}.members[{slot_label}].{field}",
                    member_slot=member_slot,
                )
        images = member.get("images")
        if prefix == "team_zh":
            if not isinstance(images, dict):
                _add_missing_required_issue(
                    issues,
                    f"{prefix}.members[{slot_label}].images",
                    member_slot=member_slot,
                )
                continue
            pokemon_image = images.get("pokemon")
            if not isinstance(pokemon_image, dict) or not _has_value(pokemon_image, "status"):
                _add_missing_required_issue(
                    issues,
                    f"{prefix}.members[{slot_label}].images.pokemon.status",
                    member_slot=member_slot,
                )
            item_image = images.get("item")
            if not isinstance(item_image, dict) or not _has_value(item_image, "status"):
                _add_missing_required_issue(
                    issues,
                    f"{prefix}.members[{slot_label}].images.item.status",
                    member_slot=member_slot,
                )


def validate_translated_team(
    raw_team: dict,
    team_zh: dict,
    assets_config: dict,
    template_name: str | None = None,
) -> dict:
    issues = []
    template_registry = assets_config.get("templates", {})
    default_template = assets_config.get("default_template")

    _validate_required_meta_fields(issues, raw_team, "raw_team")
    _validate_required_member_fields(issues, raw_team, "raw_team", ("slot", "species", "moves"))

    _validate_required_meta_fields(issues, team_zh, "team_zh")
    team_zh_meta = team_zh.get("meta") if isinstance(team_zh.get("meta"), dict) else {}
    if not _has_value(team_zh_meta, "image_source_base_url"):
        _add_missing_required_issue(issues, "team_zh.meta.image_source_base_url")
    _validate_required_member_fields(
        issues,
        team_zh,
        "team_zh",
        ("slot", "species", "moves_zh"),
    )

    if default_template not in template_registry:
        issues.append(
            {
                "code": "invalid_default_template",
                "message": f"default template {default_template!r} is not registered",
            }
        )
    if template_name and template_name not in template_registry:
        issues.append(
            {
                "code": "invalid_template_name",
                "template_name": template_name,
                "message": f"template {template_name!r} is not registered",
            }
        )
    for unresolved in team_zh.get("unresolved_terms", []):
        issues.append(
            {
                "code": "missing_translation",
                "field": unresolved["field"],
                "term": unresolved["term"],
                "member_slot": unresolved["member_slot"],
            }
        )
    for member in team_zh.get("members", []):
        if member["images"]["pokemon"]["status"] != "ok":
            issues.append(
                {
                    "code": "missing_pokemon_image",
                    "field": "images.pokemon",
                    "term": member["species"],
                    "member_slot": member["slot"],
                }
            )
        if member.get("item") and member["images"]["item"]["status"] != "ok":
            issues.append(
                {
                    "code": "missing_item_image",
                    "field": "images.item",
                    "term": member["item"],
                    "member_slot": member["slot"],
                }
            )
    return {"status": "ok" if not issues else "error", "issues": issues}
