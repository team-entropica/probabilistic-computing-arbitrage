from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    import plotly.graph_objects as go
except Exception as exc:  # pragma: no cover - runtime guard
    raise SystemExit(
        "plotly is required for this script. Install with `pip install plotly`."
    ) from exc


ROOT_DIR = Path(__file__).resolve().parents[2]
FETCH_PATH = (
    ROOT_DIR
    / "src"
    / "apis"
    / "pinnacle-odds"
    / "special-markets"
    / "fetch_special_markets.py"
)
PLOTS_DIR = ROOT_DIR / "src" / "visualizations" / "plots"


def load_fetch_module():
    """Load the special-markets fetcher despite the dash in its path."""
    spec = importlib.util.spec_from_file_location("pinnacle_special_fetch", FETCH_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {FETCH_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pinnacle_special_fetch"] = module
    spec.loader.exec_module(module)
    return module


def specials_to_rows(specials: List[Dict[str, Any]], limit: int | None = None):
    rows: List[Dict[str, str]] = []
    iterable = specials if limit is None else specials[:limit]
    for special in iterable:
        outcomes = special.get("lines", {}).values()
        outcome_str = " | ".join(
            f"{line.get('name')}: {line.get('price')}" for line in outcomes
        )
        rows.append(
            {
                "category": special.get("category", "Unknown"),
                "market": special.get("name", ""),
                "outcomes": outcome_str or "No lines",
            }
        )
    return rows


def plot_specials(
    rows: List[Dict[str, str]],
    title: str,
    output_name: str = "pinnacle_special_markets.html",
):
    if not rows:
        raise ValueError("No special markets to visualize.")

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["Category", "Market", "Outcomes"],
                    fill_color="#1f5eff",
                    font_color="white",
                    align="left",
                ),
                cells=dict(
                    values=[
                        [row["category"] for row in rows],
                        [row["market"] for row in rows],
                        [row["outcomes"] for row in rows],
                    ],
                    align="left",
                ),
            )
        ]
    )
    fig.update_layout(title=title, height=min(1200, 120 + 30 * len(rows)))

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PLOTS_DIR / output_name
    fig.write_html(output_path, include_plotlyjs="cdn")
    print(f"Saved special markets table to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Render Pinnacle special markets for a single football match."
    )
    parser.add_argument(
        "--event-id",
        help="Optional Pinnacle event ID. If omitted, the first prematch event from main leagues is used.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of specials to include in the table. Default: 50",
    )
    args = parser.parse_args()

    fetch_module = load_fetch_module()
    session = fetch_module.build_session()

    if args.event_id:
        event_id = args.event_id
        event_description = f"Event {event_id}"
    else:
        event = fetch_module.get_first_event(session)
        event_id = str(event["event_id"])
        event_description = f"{event.get('home', '?')} vs {event.get('away', '?')}"

    specials = fetch_module.get_special_markets_for_event(session, event_id)
    rows = specials_to_rows(specials, limit=args.limit)

    print(f"Loaded {len(rows)} specials for {event_description}.")
    if not rows:
        return

    plot_specials(
        rows,
        title=f"Special markets for {event_description}",
        output_name="pinnacle_special_markets.html",
    )


if __name__ == "__main__":
    main()
