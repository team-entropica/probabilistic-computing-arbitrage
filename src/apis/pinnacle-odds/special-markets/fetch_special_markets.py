from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone
import csv

import requests

BASE_URL = "https://pinnacle-odds.p.rapidapi.com"
FOOTBALL_SPORT_ID = "1"
MAIN_FOOTBALL_LEAGUE_IDS_SHORT = "2627,2196,1842,2436,2036,1980"
ROOT_DIR = Path(__file__).resolve().parents[4]
DEFAULT_CSV_PATH = (
    ROOT_DIR / "src" / "visualizations" / "plots" / "pinnacle_special_markets.csv"
)
DEFAULT_WIDE_CSV_PATH = (
    ROOT_DIR / "src" / "visualizations" / "plots" / "pinnacle_special_markets_wide.csv"
)
DEFAULT_KEY_PATH = (
    ROOT_DIR
    / "src"
    / "visualizations"
    / "plots"
    / "pinnacle_special_markets_column_key.json"
)


def get_api_key() -> str:
    """
    Prefer an environment variable but fall back to the checked-in key so the
    script works out of the box.
    """
    return os.getenv(
        "PINNACLE_RAPIDAPI_KEY",
        "3ca67aa802msh24fe1c798e3001ap1285dbjsndc55695dd39d",
    )


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "x-rapidapi-key": get_api_key(),
            "x-rapidapi-host": "pinnacle-odds.p.rapidapi.com",
        }
    )
    return session


def get_first_event(
    session: requests.Session, leagues: str = MAIN_FOOTBALL_LEAGUE_IDS_SHORT
) -> Dict[str, Any]:
    response = session.get(
        f"{BASE_URL}/kit/v1/markets",
        params={
            "sport_id": FOOTBALL_SPORT_ID,
            "event_type": "prematch",
            "league_ids": leagues,
            "is_have_odds": True,
        },
    )
    response.raise_for_status()
    payload = response.json()
    events: List[Dict[str, Any]] = payload.get("events", [])
    if not events:
        raise RuntimeError("No football events returned for the requested leagues.")
    return events[0]


def get_special_markets_for_event(
    session: requests.Session, event_id: str, include_odds: bool = True
) -> Dict[str, Any]:
    response = session.get(
        f"{BASE_URL}/kit/v1/special-markets",
        params={
            "sport_id": FOOTBALL_SPORT_ID,
            "event_ids": str(event_id),
            "is_have_odds": include_odds,
        },
    )
    response.raise_for_status()
    return response.json()


def summarize_specials(
    specials: List[Dict[str, Any]], limit: int = 15
) -> List[str]:
    lines: List[str] = []
    for special in specials[:limit]:
        outcomes = special.get("lines", {}).values()
        price_summary = ", ".join(
            f"{line.get('name')}: {line.get('price')}" for line in outcomes
        )
        lines.append(
            f"[{special.get('category', '?')}] {special.get('name')} -> {price_summary}"
        )
    return lines


def _normalize_text(
    text: str | None, home_team: str, away_team: str, category: str | None
) -> str:
    if not text:
        return ""
    cleaned = text.replace(home_team, "Home").replace(away_team, "Away")
    if category and category.lower() == "team props":
        cleaned = cleaned.replace("Team Props - ", "").replace("Team Props ", "")
    cleaned = cleaned.replace("?", "").strip()
    return cleaned


def specials_to_rows(specials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Flatten special markets into one row per outcome.
    """
    rows: List[Dict[str, Any]] = []
    for special in specials:
        event = special.get("event", {}) or {}
        home_team = event.get("home", "Home Team")
        away_team = event.get("away", "Away Team")
        category = special.get("category")

        market_label = _normalize_text(
            special.get("name"), home_team, away_team, category
        )

        meta = {
            "special_id": special.get("special_id"),
            "event_id": special.get("event_id"),
            "league_id": special.get("league_id"),
            "category": special.get("category"),
            "market_name": market_label,
            "bet_type": special.get("bet_type"),
            "starts": special.get("starts"),
            "cutoff": special.get("cutoff"),
            "home_team": home_team,
            "away_team": away_team,
        }
        for line in special.get("lines", {}).values():
            outcome_label = _normalize_text(
                line.get("name"), home_team, away_team, category
            )
            rows.append(
                {
                    **meta,
                    "line_id": line.get("line_id"),
                    "outcome_id": line.get("id"),
                    "outcome_name": outcome_label,
                    "rot_num": line.get("rot_num"),
                    "handicap": line.get("handicap"),
                    "price": line.get("price"),
                }
            )
    return rows


def pivot_outcomes_wide(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pivot outcomes so each category/market/outcome becomes a column and the
    rows are indexed by fetch time.
    Returns a dict with headers and data rows ready for CSV writing.
    """
    if not rows:
        return {"headers": [], "data": []}

    # One fetch per run, so use the first fetched_at value.
    fetch_time = rows[0].get("fetched_at", "")
    columns = sorted({row["column_key"] for row in rows})

    row_map = {col: None for col in columns}
    for row in rows:
        row_map[row["column_key"]] = row.get("price")

    return {
        "headers": ["fetched_at"] + columns,
        "data": [[fetch_time] + [row_map.get(col) for col in columns]],
    }


def build_column_key(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    Produce a mapping from column key to raw details for readability.
    """
    key: Dict[str, Dict[str, str]] = {}
    for row in rows:
        col = row.get("column_key")
        if not col:
            continue
        key[col] = {
            "category": row.get("category", ""),
            "market_name": row.get("market_name", ""),
            "outcome_name": row.get("outcome_name", ""),
            "home_team": row.get("home_team", ""),
            "away_team": row.get("away_team", ""),
        }
    return key


def _append_long_csv(path: Path, rows: List[Dict[str, Any]], event_id: str):
    """
    Append rows to the long-form CSV, preserving a match comment line.
    If the file does not exist, write headers. If headers change, rewrite.
    """
    if not rows:
        return

    match_line = (
        f"# Match: {rows[0]['home_team']} vs {rows[0]['away_team']} "
        f"(event {event_id})"
    )
    existing_headers: List[str] = []
    existing_rows: List[Dict[str, Any]] = []

    if path.exists() and path.stat().st_size > 0:
        with path.open("r", encoding="utf-8") as f:
            first = f.readline()
            if not first.startswith("#"):
                # No comment; treat as header line
                f.seek(0)
            else:
                # skip comment line already read
                pass
            reader = csv.DictReader(f)
            existing_headers = reader.fieldnames or []
            for row in reader:
                # Drop any None keys from malformed rows
                row.pop(None, None)
                if any(row.values()):
                    existing_rows.append(row)

    # Use union of headers to handle new columns
    new_headers_set = set(existing_headers) | set(rows[0].keys())
    headers = existing_headers if existing_headers else list(rows[0].keys())
    headers = [h for h in headers if h is not None]
    for h in rows[0].keys():
        if h is not None and h not in headers:
            headers.append(h)
    for h in existing_headers:
        if h is not None and h not in headers:
            headers.append(h)

    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(match_line + "\n")
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        if existing_rows:
            writer.writerows([{k: v for k, v in r.items() if k in headers} for r in existing_rows])
        writer.writerows([{k: v for k, v in r.items() if k in headers} for r in rows])


def _append_wide_csv(
    path: Path, wide: Dict[str, Any], rows: List[Dict[str, Any]], event_id: str
):
    """
    Append the wide-form single-row snapshot. If headers change, rewrite
    existing data with new columns.
    """
    if not rows or not wide.get("headers"):
        return

    match_line = (
        f"# Match: {rows[0]['home_team']} vs {rows[0]['away_team']} "
        f"(event {event_id})"
    )
    new_headers = wide["headers"]
    new_data_rows = wide["data"]

    existing_headers: List[str] = []
    existing_data: List[List[str]] = []

    if path.exists() and path.stat().st_size > 0:
        with path.open("r", encoding="utf-8") as f:
            first = f.readline()
            if not first.startswith("#"):
                f.seek(0)
            reader = csv.reader(f)
            header_line = next(reader, [])
            existing_headers = header_line
            for row in reader:
                existing_data.append(row)

    # Merge headers if new columns appear
    headers = list(existing_headers) if existing_headers else []
    for h in new_headers:
        if h not in headers:
            headers.append(h)

    def pad_row(row: List[Any], header_ref: List[str]) -> List[str]:
        # row corresponds to new_headers ordering
        row_map = {h: (row[i] if i < len(row) else "") for i, h in enumerate(new_headers)}
        return ["" if row_map.get(h) is None else str(row_map.get(h)) for h in header_ref]

    merged_existing: List[List[str]] = []
    if existing_data and existing_headers:
        # Re-align old rows to merged headers
        for r in existing_data:
            row_map = {existing_headers[i]: r[i] if i < len(r) else "" for i in range(len(existing_headers))}
            merged_existing.append([row_map.get(h, "") for h in headers])

    merged_new = [pad_row(r, headers) for r in new_data_rows]

    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(match_line + "\n")
        writer = csv.writer(f)
        writer.writerow(headers)
        if merged_existing:
            writer.writerows(merged_existing)
        writer.writerows(merged_new)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch all special markets for a single football match."
    )
    parser.add_argument(
        "--event-id",
        help="Optional Pinnacle event ID. If omitted, the first prematch event from main leagues is used.",
    )
    parser.add_argument(
        "--leagues",
        default=MAIN_FOOTBALL_LEAGUE_IDS_SHORT,
        help="Comma-separated league IDs to search when auto-selecting a match.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the raw specials JSON.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=(
            "Path to write the specials as a CSV (one row per outcome). "
            f"Default: {DEFAULT_CSV_PATH}"
        ),
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=10,
        help="Number of specials to preview in stdout. Default: 10",
    )
    parser.add_argument(
        "--wide-csv",
        type=Path,
        default=DEFAULT_WIDE_CSV_PATH,
        help=(
            "Path to write a pivoted CSV (timestamps as rows, category/market/outcome "
            f"as columns). Default: {DEFAULT_WIDE_CSV_PATH}"
        ),
    )
    parser.add_argument(
        "--key-output",
        type=Path,
        default=DEFAULT_KEY_PATH,
        help=(
            "Path to write a JSON key mapping shorthand column headers to details. "
            f"Default: {DEFAULT_KEY_PATH}"
        ),
    )
    args = parser.parse_args()

    session = build_session()

    if args.event_id:
        event_id = args.event_id
        event_description = f"event {event_id}"
    else:
        event = get_first_event(session, leagues=args.leagues)
        event_id = str(event["event_id"])
        event_description = f"{event.get('home', '?')} vs {event.get('away', '?')}"

    specials = get_special_markets_for_event(session, event_id)
    specials_list = specials.get("specials", [])
    api_last = specials.get("last")
    fetched_at = datetime.now(timezone.utc).isoformat()
    print(f"Fetched {len(specials_list)} special markets for {event_description}.")
    if api_last:
        print(f"API reported last timestamp: {api_last}")

    if specials_list:
        preview_lines = summarize_specials(specials_list, limit=args.preview)
        print("\nPreview:")
        for line in preview_lines:
            print(f" - {line}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(specials, indent=2))
        print(f"Wrote raw specials JSON to {args.output}")

    rows = specials_to_rows(specials_list)
    for row in rows:
        row["fetched_at"] = fetched_at
        row["api_last"] = api_last
        row["column_key"] = (
            (row.get("category") or "Uncategorized")
            + " | "
            + (row.get("market_name") or "Unknown Market")
            + " | "
            + (row.get("outcome_name") or "Outcome")
        )
    print(f"Flattened to rows with {len(rows)} outcomes.")

    csv_path = args.csv or DEFAULT_CSV_PATH
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _append_long_csv(csv_path, rows, event_id)
    print(f"Wrote specials dataframe to {csv_path}")

    wide_path = args.wide_csv or DEFAULT_WIDE_CSV_PATH
    wide = pivot_outcomes_wide(rows)
    wide_path.parent.mkdir(parents=True, exist_ok=True)
    _append_wide_csv(wide_path, wide, rows, event_id)
    print(f"Wrote pivoted timeseries-friendly CSV to {wide_path}")

    key = build_column_key(rows)
    key_path = args.key_output or DEFAULT_KEY_PATH
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(json.dumps(key, indent=2))
    print(f"Wrote column header key to {key_path}")


if __name__ == "__main__":
    main()
