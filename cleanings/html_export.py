"""Render the cleanings calendar as a self-contained HTML file."""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from cleanings.calendar_model import (
    LISTING_COLORS,
    LISTING_ROW_ORDER,
    WEEKEND_COLOR,
    GridColumn,
    OccupiedCell,
    build_occupied_cells,
    month_grid,
)
from cleanings.main import MONTHS_PT

_CSS = """
:root {
  --bg: #f4f5f7;
  --card: #ffffff;
  --text: #1a1a1a;
  --muted: #6b7280;
  --border: #d1d5db;
  --nav-bg: #ffffff;
  --nav-shadow: 0 1px 3px rgba(0,0,0,.08);
  --day-size: 2rem;
  --listing-size: 2.25rem;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.4;
}
header {
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 1rem 1.25rem 1.25rem;
}
header h1 { margin: 0 0 .75rem; font-size: 1.5rem; font-weight: 600; }
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem 1rem;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  font-size: .875rem;
  font-weight: 500;
}
.legend-swatch {
  width: 1rem;
  height: 1rem;
  border-radius: 3px;
  border: 1px solid rgba(0,0,0,.12);
}
nav.month-nav {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  flex-wrap: wrap;
  gap: .35rem;
  padding: .6rem 1rem;
  background: var(--nav-bg);
  box-shadow: var(--nav-shadow);
  border-bottom: 1px solid var(--border);
  -webkit-overflow-scrolling: touch;
}
nav.month-nav a {
  color: #2563eb;
  text-decoration: none;
  font-size: .8rem;
  padding: .2rem .45rem;
  border-radius: 4px;
  flex: 0 0 auto;
}
nav.month-nav a:hover { background: #eff6ff; }
main {
  padding: 1rem;
  max-width: 1400px;
  margin: 0 auto;
  padding-left: max(1rem, env(safe-area-inset-left));
  padding-right: max(1rem, env(safe-area-inset-right));
}
.month-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 1.25rem;
  overflow: hidden;
}
.month-card h2 {
  margin: 0;
  padding: .75rem 1rem;
  font-size: 1.1rem;
  background: #f9fafb;
  border-bottom: 1px solid var(--border);
}
.month-scroll {
  overflow-x: auto;
  padding: .75rem 1rem 1rem;
  -webkit-overflow-scrolling: touch;
  scroll-padding-left: 2.6rem;
}
.grid {
  display: grid;
  grid-template-columns: 2.5rem repeat(37, var(--day-size));
  gap: 2px;
  width: max-content;
  min-width: 100%;
}
.cell {
  width: var(--day-size);
  min-width: var(--day-size);
  height: var(--day-size);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: .7rem;
  border: 1px solid var(--border);
  border-radius: 3px;
  background: #fff;
}
.cell.header {
  background: #f3f4f6;
  font-weight: 600;
  color: var(--muted);
  font-size: .65rem;
}
.cell.weekday-header {
  cursor: pointer;
  user-select: none;
}
.cell.weekday-header.is-palm {
  font-size: .85rem;
  line-height: 1;
}
.cell.day-num {
  font-weight: 600;
  font-size: .75rem;
}
.cell.weekend-empty { background: var(--weekend-bg, #ebedf0); }
.cell.listing-label {
  width: 2.5rem;
  min-width: 2.5rem;
  font-weight: 700;
  font-size: .75rem;
  background: #f9fafb;
  border-color: transparent;
  justify-content: flex-end;
  padding-right: .35rem;
  position: sticky;
  left: 0;
  z-index: 2;
  box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
}
.cell.listing-row {
  height: var(--listing-size);
  font-weight: 600;
  font-size: .65rem;
  padding: 0 .15rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cell.stay { color: #111; border-color: rgba(0,0,0,.15); }
.cell.stay-comment {
  cursor: pointer;
  position: relative;
  touch-action: manipulation;
}
.cell.stay-comment:hover { outline: 2px solid #2563eb; outline-offset: -2px; }
.cell.stay-comment:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: -2px;
}
.cell.stay-comment.has-comment {
  border: 2px dashed #1d4ed8 !important;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
}
.comment-backdrop {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.35);
  z-index: 100;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.comment-backdrop.open { display: flex; }
.comment-dialog {
  background: var(--card);
  border-radius: 10px;
  padding: 1.25rem;
  width: min(24rem, 100%);
  box-shadow: 0 8px 30px rgba(0,0,0,.18);
}
.comment-dialog h3 { margin: 0 0 .35rem; font-size: 1rem; }
.comment-dialog .meta {
  margin: 0 0 .75rem;
  font-size: .8rem;
  color: var(--muted);
}
.comment-dialog textarea {
  width: 100%;
  min-height: 5rem;
  resize: vertical;
  font: inherit;
  padding: .5rem .6rem;
  border: 1px solid var(--border);
  border-radius: 6px;
}
.comment-actions {
  display: flex;
  gap: .5rem;
  justify-content: flex-end;
  margin-top: .75rem;
}
.comment-actions button {
  font: inherit;
  padding: .4rem .85rem;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: #f9fafb;
  cursor: pointer;
}
.comment-actions button.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.comment-actions button.danger { color: #b91c1c; }
@media (hover: none) {
  .cell.stay-comment:hover { outline: none; }
  .cell.stay-comment:active {
    outline: 2px solid #2563eb;
    outline-offset: -2px;
  }
}
@media (max-width: 768px) {
  nav.month-nav {
    flex-wrap: nowrap;
    overflow-x: auto;
    gap: .45rem;
    padding: .55rem max(.75rem, env(safe-area-inset-left));
    scroll-snap-type: x proximity;
  }
  nav.month-nav a {
    font-size: .85rem;
    padding: .45rem .7rem;
    min-height: 2.25rem;
    display: inline-flex;
    align-items: center;
    background: #f3f4f6;
    scroll-snap-align: start;
  }
  header {
    padding: .85rem max(.85rem, env(safe-area-inset-left))
      1rem max(.85rem, env(safe-area-inset-right));
  }
  header h1 { font-size: 1.2rem; margin-bottom: .55rem; }
  .legend { gap: .4rem .65rem; }
  .legend-item { font-size: .8rem; }
  main { padding-top: .65rem; padding-bottom: max(1rem, env(safe-area-inset-bottom)); }
  .month-card { border-radius: 10px; margin-bottom: 1rem; }
  .month-card h2 {
    font-size: 1rem;
    padding: .65rem .85rem;
    position: sticky;
    left: 0;
  }
  .month-scroll {
    padding: .55rem .65rem .85rem;
  }
  .month-scroll::after {
    content: "Deslize para ver mais dias →";
    display: block;
    margin-top: .45rem;
    text-align: center;
    font-size: .72rem;
    color: var(--muted);
  }
  .comment-backdrop.open {
    align-items: flex-end;
    padding: 0;
  }
  .comment-dialog {
    width: 100%;
    max-width: none;
    border-radius: 14px 14px 0 0;
    padding: 1rem 1rem calc(1rem + env(safe-area-inset-bottom));
  }
  .comment-dialog textarea {
    min-height: 6.5rem;
    font-size: 1rem;
  }
  .comment-actions {
    flex-wrap: wrap;
  }
  .comment-actions button {
    flex: 1 1 30%;
    min-height: 2.75rem;
    font-size: .95rem;
  }
}
@media (max-width: 640px) {
  :root {
    --day-size: 2.15rem;
    --listing-size: 2.35rem;
  }
  .cell {
    font-size: .72rem;
    border-radius: 4px;
  }
  .cell.header { font-size: .68rem; }
  .cell.day-num { font-size: .78rem; }
  .cell.listing-label {
    width: 2.35rem;
    min-width: 2.35rem;
    font-size: .72rem;
  }
  .cell.listing-row {
    font-size: .68rem;
    padding: 0 .2rem;
  }
  .grid { gap: 3px; }
}
"""


def stay_cell_id(listing: str, day: date) -> str:
    """Stable DOM / localStorage key for a stay day cell."""
    return f"{listing}-{day.strftime('%Y%m%d')}"


def _storage_key(year: int) -> str:
    return f"airbnb-cleanings-comments-{year}"


def _cell_title(cell: OccupiedCell) -> str:
    parts = [
        f"{cell.listing}: {cell.start_date.isoformat()} → {cell.end_date.isoformat()}",
    ]
    if cell.guest_label:
        parts.append(f"Hóspedes: {cell.guest_label}")
    return " | ".join(parts)


def _render_month(
    year: int,
    month: int,
    month_name: str,
    occupied: dict[date, dict[str, OccupiedCell]],
) -> str:
    columns = month_grid(year, month)
    weekday_row = columns  # one header per column slot

    grid_style = f"--weekend-bg: {html.escape(WEEKEND_COLOR)};"
    parts: list[str] = [
        f'<section class="month-card" id="{html.escape(month_name.lower())}">',
        f"<h2>{html.escape(month_name)}</h2>",
        '<div class="month-scroll">',
        f'<div class="grid" style="{grid_style}">',
        '<div class="cell listing-label"></div>',
    ]

    for col in weekday_row:
        label = html.escape(col.weekday_label)
        parts.append(
            f'<div class="cell header weekday-header" data-default="{label}">'
            f"{label}</div>"
        )

    parts.append('<div class="cell listing-label">dia</div>')
    for col in columns:
        if col.day is None:
            cls = "cell"
            if col.is_weekend:
                cls += " weekend-empty"
            parts.append(f'<div class="{cls}"></div>')
        else:
            cls = "cell day-num"
            if col.is_weekend:
                cls += " weekend-empty"
            parts.append(f'<div class="{cls}">{col.day}</div>')

    for listing in LISTING_ROW_ORDER:
        color = LISTING_COLORS[listing]
        parts.append(
            f'<div class="cell listing-label" style="color:{color}">'
            f"{html.escape(listing)}</div>"
        )
        for col in columns:
            if col.day is None:
                cls = "cell listing-row"
                if col.is_weekend:
                    cls += " weekend-empty"
                parts.append(f'<div class="{cls}"></div>')
                continue

            day_date = date(year, month, col.day)
            stay = occupied.get(day_date, {}).get(listing)
            if stay:
                title = html.escape(_cell_title(stay), quote=True)
                label = html.escape(stay.guest_label)
                cell_id = stay_cell_id(listing, day_date)
                parts.append(
                    f'<div id="{html.escape(cell_id)}"'
                    f' class="cell listing-row stay stay-comment"'
                    f' style="background:{color}"'
                    f' title="{title}"'
                    f' data-listing="{html.escape(listing)}"'
                    f' data-date="{day_date.strftime("%Y%m%d")}"'
                    f' role="button" tabindex="0">{label}</div>'
                )
            else:
                cls = "cell listing-row"
                if col.is_weekend:
                    cls += " weekend-empty"
                parts.append(f'<div class="{cls}"></div>')

    parts.extend(["</div>", "</div>", "</section>"])
    return "\n".join(parts)


def render_cleaning_html(*, year: int, bookings: list[dict]) -> str:
    occupied = build_occupied_cells(year, bookings)

    legend_items = "".join(
        f'<span class="legend-item">'
        f'<span class="legend-swatch" style="background:{color}"></span>'
        f"{html.escape(label)}</span>"
        for label, color in LISTING_COLORS.items()
    )

    nav_links = "".join(
        f'<a href="#{html.escape(name.lower())}">{html.escape(name)}</a>'
        for name in MONTHS_PT
    )

    months_html = "\n".join(
        _render_month(year, month, name, occupied)
        for month, name in enumerate(MONTHS_PT, start=1)
    )

    storage_key = _storage_key(year)
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#f4f5f7">
  <meta name="mobile-web-app-capable" content="yes">
  <title>Calendário limpezas {year}</title>
  <style>{_CSS}</style>
</head>
<body data-year="{year}">
  <header>
    <h1>Calendário de limpezas {year}</h1>
    <div class="legend">{legend_items}</div>
  </header>
  <nav class="month-nav" aria-label="Meses">{nav_links}</nav>
  <main>
{months_html}
  </main>
  <div class="comment-backdrop" id="comment-backdrop" hidden>
    <div class="comment-dialog" role="dialog" aria-labelledby="comment-title">
      <h3 id="comment-title">Comentário de limpeza</h3>
      <p class="meta" id="comment-meta"></p>
      <textarea id="comment-input" placeholder="Notas para este dia…"></textarea>
      <div class="comment-actions">
        <button type="button" class="danger" id="comment-delete">Apagar</button>
        <button type="button" id="comment-cancel">Cancelar</button>
        <button type="button" class="primary" id="comment-save">Guardar</button>
      </div>
    </div>
  </div>
  <script>
(function () {{
  const STORAGE_KEY = {storage_key!r};
  let activeCellId = null;

  function loadComments() {{
    try {{
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}");
    }} catch (_err) {{
      return {{}};
    }}
  }}

  function saveComments(comments) {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(comments));
  }}

  function applySavedComments() {{
    const comments = loadComments();
    document.querySelectorAll(".stay-comment").forEach((cell) => {{
      const text = comments[cell.id];
      const hasComment = Boolean(text && text.trim());
      if (!cell.dataset.baseTitle) {{
        cell.dataset.baseTitle = cell.getAttribute("title") || "";
      }}
      cell.classList.toggle("has-comment", hasComment);
      cell.title = hasComment
        ? cell.dataset.baseTitle + " | Nota: " + text.trim()
        : cell.dataset.baseTitle;
    }});
  }}

  const backdrop = document.getElementById("comment-backdrop");
  const meta = document.getElementById("comment-meta");
  const input = document.getElementById("comment-input");

  function openDialog(cell) {{
    activeCellId = cell.id;
    const listing = cell.dataset.listing;
    const date = cell.dataset.date;
    const formatted = date.slice(0, 4) + "-" + date.slice(4, 6) + "-" + date.slice(6, 8);
    meta.textContent = listing + " · " + formatted;
    input.value = loadComments()[activeCellId] || "";
    backdrop.hidden = false;
    backdrop.classList.add("open");
    input.focus();
  }}

  function closeDialog() {{
    backdrop.classList.remove("open");
    backdrop.hidden = true;
    activeCellId = null;
  }}

  document.querySelectorAll(".stay-comment").forEach((cell) => {{
    cell.addEventListener("click", () => openDialog(cell));
    cell.addEventListener("keydown", (event) => {{
      if (event.key === "Enter" || event.key === " ") {{
        event.preventDefault();
        openDialog(cell);
      }}
    }});
  }});

  document.getElementById("comment-cancel").addEventListener("click", closeDialog);
  backdrop.addEventListener("click", (event) => {{
    if (event.target === backdrop) closeDialog();
  }});

  document.getElementById("comment-save").addEventListener("click", () => {{
    if (!activeCellId) return;
    const comments = loadComments();
    const text = input.value.trim();
    if (text) {{
      comments[activeCellId] = text;
    }} else {{
      delete comments[activeCellId];
    }}
    saveComments(comments);
    applySavedComments();
    closeDialog();
  }});

  document.getElementById("comment-delete").addEventListener("click", () => {{
    if (!activeCellId) return;
    const comments = loadComments();
    delete comments[activeCellId];
    saveComments(comments);
    input.value = "";
    applySavedComments();
    closeDialog();
  }});

  applySavedComments();

  const PALM_ICON = "\U0001f334";
  document.querySelectorAll(".weekday-header").forEach((cell) => {{
    cell.addEventListener("dblclick", () => {{
      if (cell.classList.contains("is-palm")) {{
        cell.textContent = cell.dataset.default;
        cell.classList.remove("is-palm");
      }} else {{
        cell.textContent = PALM_ICON;
        cell.classList.add("is-palm");
      }}
    }});
  }});
}})();
  </script>
</body>
</html>
"""


def write_cleaning_html(
    *,
    year: int,
    bookings: list[dict],
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_cleaning_html(year=year, bookings=bookings),
        encoding="utf-8",
    )
    return output_path
