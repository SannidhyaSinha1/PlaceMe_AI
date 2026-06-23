"""Matplotlib charts rendered server-side to base64 PNG (rule #3: Agg backend)."""

from __future__ import annotations

import base64
import io
import logging

import matplotlib

matplotlib.use("Agg")  # headless backend — must precede pyplot import
import matplotlib.pyplot as plt  # noqa: E402

logger = logging.getLogger(__name__)

_PALETTE = ["#6366f1", "#22c55e", "#f59e0b", "#3b82f6", "#10b981", "#ef4444", "#8b5cf6"]


def _fg(dark: bool) -> str:
    """Foreground (text/axis) colour readable on the active theme's surface."""
    return "#cbd5e1" if dark else "#334155"


def _style_axes(ax, fg: str) -> None:
    """Theme the spines, ticks and labels so text stays legible in both modes."""
    ax.tick_params(colors=fg, labelsize=9)
    for side, spine in ax.spines.items():
        if side in ("top", "right"):
            spine.set_visible(False)
        else:
            spine.set_color(fg)
            spine.set_alpha(0.3)


def _to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", transparent=True, dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def status_pie_chart(status_counts: dict, dark: bool = False) -> str | None:
    if not status_counts:
        return None
    try:
        fg = _fg(dark)
        labels = list(status_counts.keys())
        values = list(status_counts.values())
        fig, ax = plt.subplots(figsize=(6, 4))
        _, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.0f%%",
            colors=_PALETTE[: len(values)], startangle=140,
            textprops={"fontsize": 10, "color": fg},
        )
        # Percentages sit on the coloured wedges → keep them white for contrast.
        for at in autotexts:
            at.set_color("#ffffff")
            at.set_fontweight("bold")
        ax.set_title("Application Status", fontsize=13, weight="bold", color=fg)
        ax.axis("equal")
        return _to_b64(fig)
    except Exception as exc:  # noqa: BLE001
        logger.warning("status_pie_chart failed: %s", exc)
        return None


def skill_gap_bar_chart(skill_demand: list[dict], dark: bool = False) -> str | None:
    if not skill_demand:
        return None
    try:
        fg = _fg(dark)
        skills = [d["skill"] for d in skill_demand][::-1]
        counts = [d["count"] for d in skill_demand][::-1]
        fig, ax = plt.subplots(figsize=(6, max(3, len(skills) * 0.45)))
        ax.barh(skills, counts, color="#6366f1")
        ax.set_title("Most In-Demand Skills (Gaps)", fontsize=13, weight="bold", color=fg)
        ax.set_xlabel("Opportunities requiring it", color=fg)
        _style_axes(ax, fg)
        for i, v in enumerate(counts):
            ax.text(v + 0.05, i, str(v), va="center", fontsize=9, color=fg)
        fig.tight_layout()
        return _to_b64(fig)
    except Exception as exc:  # noqa: BLE001
        logger.warning("skill_gap_bar_chart failed: %s", exc)
        return None
