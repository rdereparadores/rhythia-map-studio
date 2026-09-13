"""Musical movement intents and bounded beam search over future note sequences."""

import hashlib
import math
from functools import lru_cache

import numpy as np

from .models import check_cancel
from .profiles import PLANNER_RULES

CELLS = tuple((x, y) for y in range(3) for x in range(3))
DISTANCE = np.array([[math.dist(a, b) for b in CELLS] for a in CELLS])


def stable_seed(seed, group):
    return int.from_bytes(hashlib.sha256(f"{seed}/{group}".encode()).digest()[:4], "little")


@lru_cache(maxsize=12000)
def shape_key(positions):
    """Canonical translation/reflection/90° rotation invariant trajectory signature."""
    coords = [CELLS[i] for i in positions]
    x0, y0 = coords[0]
    delta = [(x - x0, y - y0) for x, y in coords]
    variants = []
    for swap in (False, True):
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            variants.append(tuple((sx * (y if swap else x), sy * (x if swap else y)) for x, y in delta))
    return min(variants)


def repetition_cost(history, candidate):
    sequence = history + (candidate,)
    cost = 0.0
    if len(sequence) >= 8:
        recent = shape_key(sequence[-4:])
        for distance in (4, 8, 12):
            if len(sequence) >= distance + 4 and recent == shape_key(sequence[-distance - 4 : -distance]):
                cost += PLANNER_RULES.short_repeat_penalty
    if len(sequence) >= 16 and shape_key(sequence[-8:]) == shape_key(sequence[-16:-8]):
        cost += PLANNER_RULES.long_repeat_penalty
    # Discourage stationary strings independently of shape comparisons.
    if len(sequence) >= 3 and sequence[-1] == sequence[-2] == sequence[-3]:
        cost += PLANNER_RULES.stationary_repeat_penalty
    return cost


def movement_intents(events, phrase, seed):
    """A phrase-long cubic curve with musical contour, never an eight-note loop."""
    rng = np.random.default_rng(seed)
    duration = max(1, phrase["end_ms"] - phrase["start_ms"])
    intensity = phrase["intensity"]
    amplitude = 0.48 + 0.47 * intensity
    # A→B→A'→cadence is a phrase-level relation; each curve unfolds only once.
    part = phrase["part"]
    if phrase["role"] == "ending":
        p0, p3 = np.array([-0.8, -0.3]), np.array([0.25, 0.25])
    else:
        p0 = np.array([-1.0, -0.35 if part % 2 == 0 else 0.35])
        p3 = np.array([1.0, 0.35 if part % 2 == 0 else -0.35])
    bow = float(rng.choice([-1, 1])) * (0.6 + 0.3 * rng.random())
    p1, p2 = np.array([-0.55, bow]), np.array([0.55, bow])
    angle = (part % 4) * math.pi / 2 + float(rng.uniform(-0.22, 0.22))
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    pitches = [e.get("pitch", 60) for e in events if e.get("pitch_confidence", 0) > 0.15]
    median = float(np.median(pitches)) if pitches else 60.0
    spread = max(5.0, float(np.quantile(pitches, 0.9) - np.quantile(pitches, 0.1))) if pitches else 5.0
    result = []
    for event in events:
        u = float(np.clip((event["time"] - phrase["start_ms"]) / duration, 0, 1))
        point = (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u**2 * p2 + u**3 * p3
        point = 1 + amplitude * (rotation @ point)
        confidence = event.get("pitch_confidence", 0)
        if confidence > 0.15 and phrase["lead"] != "drums":
            contour_y = 1 - 0.8 * np.clip((event["pitch"] - median) / spread * 2, -1, 1)
            point[1] = point[1] * (1 - confidence * 0.65) + contour_y * confidence * 0.65
        result.append(
            dict(
                event,
                target=tuple(np.clip(point, 0, 2)),
                desired_distance=0.65 + 0.7 * intensity + 0.35 * event.get("accent", 0),
                role=phrase["role"],
                phrase_part=part,
            )
        )
    return result


def plan_positions(
    events,
    max_speed,
    style="Flowing",
    variation=1.0,
    cancel=lambda: False,
    horizon=PLANNER_RULES.horizon,
    beam_width=PLANNER_RULES.beam_width,
):
    """Plan non-overlapping horizons with a rolling 24-note motion history.

    Every event is kept: staying in place is always feasible, so geometry cannot erase
    an important musical accent. Costs combine targets, accent distance, contour,
    turns, repetition and the movement after the current note.
    """
    chosen = []
    history = ()
    for start in range(0, len(events), horizon):
        check_cancel(cancel)
        chunk = events[start : start + horizon]
        # (cost, recently chosen cell indices, choices in this horizon)
        beams = [(0.0, history, ())]
        for offset, event in enumerate(chunk):
            index = start + offset
            dt = (event["time"] - events[index - 1]["time"]) / 1000 if index else 1.0
            target = event["target"]
            expanded = []
            for cost, tail, path in beams:
                previous = tail[-1] if tail else 4
                older = tail[-2] if len(tail) > 1 else previous
                velocity = (CELLS[previous][0] - CELLS[older][0], CELLS[previous][1] - CELLS[older][1])
                for cell, position in enumerate(CELLS):
                    distance = DISTANCE[previous, cell]
                    if distance > max_speed * max(0.001, dt) + 1e-8:
                        continue
                    dx, dy = position[0] - CELLS[previous][0], position[1] - CELLS[previous][1]
                    turn = max(0.0, -(dx * velocity[0] + dy * velocity[1]))
                    step_cost = (
                        PLANNER_RULES.anchor_weight if event.get("anchor") else PLANNER_RULES.target_weight
                    ) * math.dist(position, target) ** 2
                    step_cost += (
                        PLANNER_RULES.distance_weight
                        * (distance - min(event["desired_distance"], max_speed * dt)) ** 2
                    )
                    step_cost += (
                        (
                            PLANNER_RULES.fluid_turn_weight
                            if style == "Flowing"
                            else PLANNER_RULES.jump_turn_weight
                        )
                        * turn
                        * min(1, 0.22 / max(dt, 0.02))
                    )
                    step_cost += PLANNER_RULES.stationary_weight * (cell == previous)
                    step_cost += variation * repetition_cost(tail, cell)
                    if index:
                        pitch_delta = event.get("pitch", 60) - events[index - 1].get("pitch", 60)
                        confidence = min(
                            event.get("pitch_confidence", 0), events[index - 1].get("pitch_confidence", 0)
                        )
                        if abs(pitch_delta) >= 1 and abs(pitch_delta) < 12:
                            step_cost += confidence * max(0.0, dy * np.sign(pitch_delta)) * 0.6
                    new_tail = (tail + (cell,))[-PLANNER_RULES.history_notes :]
                    expanded.append((cost + step_cost, new_tail, path + (cell,)))
            expanded.sort(key=lambda candidate: (candidate[0], candidate[2]))
            beams = expanded[:beam_width]
        _, history, positions = beams[0]
        for event, cell in zip(chunk, positions, strict=True):
            chosen.append(dict(event, X=CELLS[cell][0], Y=CELLS[cell][1]))
    return chosen


def repeat_diagnostics(notes):
    """Counts adjacent 8-note copies up to translation/rotation/reflection."""
    cells = tuple(int(round(n["Y"])) * 3 + int(round(n["X"])) for n in notes)
    matches = 0
    longest = run = 0
    for i in range(16, len(cells) + 1):
        same = shape_key(cells[i - 8 : i]) == shape_key(cells[i - 16 : i - 8])
        matches += same
        run = run + 1 if same else 0
        longest = max(longest, run)
    return dict(
        repeated_8note_windows=matches,
        longest_consecutive_repeat_windows=longest,
        windows_checked=max(0, len(cells) - 15),
    )
