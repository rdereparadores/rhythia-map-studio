"""Phrase-level lead selection and an intensity arc shared by all difficulties."""

import numpy as np

SOURCE_LABELS = {
    "vocals": "Vocals",
    "drums": "Drums",
    "bass": "Bass",
    "other": "Instruments",
    "mix": "Mix",
}


def build_arrangement(analysis, emphasis="Mix"):
    times = np.asarray(analysis["times_ms"])
    energy = np.asarray(analysis["energy"])
    sources = analysis.get("sources", {})
    options = list(sources) if sources else ["mix"]
    phrases = []
    period = 60000 / analysis["bpm"]
    for section in analysis["sections"]:
        length = section["end_ms"] - section["start_ms"]
        count = max(1, round(length / (8 * period)))
        edges = np.linspace(section["start_ms"], section["end_ms"], count + 1)
        for part in range(count):
            start, end = edges[part : part + 2]
            mask = (times >= start) & (times < end)
            if not np.any(mask):
                mask[np.argmin(abs(times - start))] = True
            phrase = dict(
                start_ms=round(start),
                end_ms=round(end),
                group=section["group"],
                part=part,
                parts=count,
                role=("intro" if part == 0 else "ending" if part == count - 1 else "development"),
                energy=float(np.mean(energy[mask])),
                lead_scores={},
            )
            for name in options:
                if name == "mix":
                    phrase["lead_scores"][name] = 1.0
                    continue
                d = sources[name]
                presence = float(np.mean(np.asarray(d["relative_energy"])[mask]))
                attack = float(np.mean(np.asarray(d["flux"])[mask]))
                pitched = float(np.mean(np.asarray(d["pitch_confidence"])[mask]))
                score = 0.7 * presence + 0.25 * min(1, attack) + 0.2 * pitched
                if name == "vocals":
                    score += 0.20 if presence > 0.23 else -0.5
                    if emphasis == "Vocals" and presence > 0.18:
                        score += 0.45
                if emphasis == "Percussion" and name == "drums":
                    score += 0.4
                if emphasis == "Tonal" and name in ("vocals", "other", "bass"):
                    score += 0.2
                phrase["lead_scores"][name] = score
            phrases.append(phrase)
    # Viterbi decoding discourages phrase-to-phrase chattering between sources.
    scores = np.array([[p["lead_scores"][name] for name in options] for p in phrases])
    cumulative = scores[0].copy()
    parents = []
    for row in scores[1:]:
        transitions = cumulative[:, None] - 0.16 * (1 - np.eye(len(options)))
        predecessor = transitions.argmax(axis=0)
        cumulative = row + transitions[predecessor, np.arange(len(options))]
        parents.append(predecessor)
    path = [int(cumulative.argmax())]
    for predecessor in reversed(parents):
        path.append(int(predecessor[path[-1]]))
    path.reverse()
    lo, hi = np.quantile([p["energy"] for p in phrases], [0.1, 0.9])
    for i, (p, lead) in enumerate(zip(phrases, path, strict=True)):
        p["lead"] = options[lead]
        p["lead_label"] = SOURCE_LABELS[p["lead"]]
        p["intensity"] = round(float(np.clip((p["energy"] - lo) / max(0.1, hi - lo), 0, 1)), 3)
        previous = phrases[i - 1]["energy"] if i else p["energy"]
        p["impact"] = round(float(np.clip((p["energy"] - previous) / max(0.1, hi - lo), 0, 1)), 3)
        # A fall in source activity near the phrase end is an audible place to breathe.
        lead_energy = np.asarray(sources[p["lead"]]["energy"]) if p["lead"] in sources else energy
        body = (times >= p["start_ms"]) & (times < p["end_ms"] - period * 0.5)
        tail = (times >= p["end_ms"] - period * 0.5) & (times < p["end_ms"])
        p["breath"] = bool(
            np.any(body) and np.any(tail) and np.mean(lead_energy[tail]) < 0.45 * np.mean(lead_energy[body])
        )
    return phrases
