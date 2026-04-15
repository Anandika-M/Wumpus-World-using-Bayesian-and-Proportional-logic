import streamlit as st
import random

GRID = 4
PRIOR_PIT = 0.2
PRIOR_WUMPUS = 1.0 / (GRID * GRID - 1)
SAFE_THRESHOLD = 0.05
MOVE_DELTA = {"UP": (1, 0), "DOWN": (-1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


def allCells():
    return [(r, c) for r in range(GRID) for c in range(GRID)]


def adjCells(r, c):
    return [
        (r + dr, c + dc)
        for dr, dc in MOVE_DELTA.values()
        if 0 <= r + dr < GRID and 0 <= c + dc < GRID
    ]


def toDisplay(r, c):
    return (GRID - 1 - r), c


def toInternal(dRow, dCol):
    return (GRID - 1 - dRow), dCol


def buildWorld():
    pitSet = set()
    for r, c in allCells():
        if random.random() < PRIOR_PIT:
            pitSet.add((r, c))

    safeCells = [p for p in allCells() if p not in pitSet]
    if not safeCells:
        pitSet.discard((0, 0))
        safeCells = [(0, 0)]
    start = random.choice(safeCells)

    wCandidates = [p for p in allCells() if p != start and p not in pitSet]
    if not wCandidates:
        wCandidates = [p for p in allCells() if p != start]
    wumpus = random.choice(wCandidates)

    gCandidates = [p for p in allCells() if p != start and p != wumpus and p not in pitSet]
    if not gCandidates:
        gCandidates = [p for p in allCells() if p != start and p != wumpus]
    gold = random.choice(gCandidates)

    return {"pits": pitSet, "wumpus": wumpus, "gold": gold,
            "wumpusAlive": True, "start": start}


def perceiveAt(world, r, c):
    nb = adjCells(r, c)
    breeze  = any(n in world["pits"] for n in nb)
    stench  = world["wumpusAlive"] and any(n == world["wumpus"] for n in nb)
    glitter = (r, c) == world["gold"]
    return breeze, stench, glitter


def initBelief(start):
    belief = {}
    for pos in allCells():
        belief[pos] = {
            "pitProb":    PRIOR_PIT,
            "wumpusProb": PRIOR_WUMPUS,
            "visited":    False,
            "breeze":     None,
            "stench":     None,
        }
    belief[start]["pitProb"]    = 0.0
    belief[start]["wumpusProb"] = 0.0
    belief[start]["visited"]    = True
    return belief


def isSafe(belief, pos):
    return belief[pos]["pitProb"] < SAFE_THRESHOLD and belief[pos]["wumpusProb"] < SAFE_THRESHOLD


def updatePitBeliefs(belief):
    # snapshot before updating so cells don't affect each other's denominators
    priorSnapshot = {pos: belief[pos]["pitProb"] for pos in allCells()}

    for pos in allCells():
        if belief[pos]["visited"]:
            belief[pos]["pitProb"] = 0.0
            continue

        visitedNbs = [nb for nb in adjCells(*pos) if belief[nb]["visited"]]
        if not visitedNbs:
            belief[pos]["pitProb"] = PRIOR_PIT
            continue

        # any no-breeze neighbor means pos can't be a pit
        if any(belief[nb]["breeze"] is False for nb in visitedNbs):
            belief[pos]["pitProb"] = 0.0
            continue

        # sequential Bayes update for each breezy neighbor
        # P(pit|B) = P(pit) / [1 - (1 - P(pit)) * q]
        # q = product of (1 - P(pit_x)) for other unknown neighbors
        currentProb = PRIOR_PIT
        breezyNbs = [nb for nb in visitedNbs if belief[nb]["breeze"] is True]

        for breezyCell in breezyNbs:
            otherUnknowns = [
                x for x in adjCells(*breezyCell)
                if x != pos and not belief[x]["visited"]
            ]
            q = 1.0
            for x in otherUnknowns:
                q *= (1.0 - priorSnapshot[x])

            pEvidence = 1.0 - (1.0 - currentProb) * q
            currentProb = currentProb / pEvidence if pEvidence > 1e-9 else 1.0

        belief[pos]["pitProb"] = max(0.0, min(1.0, currentProb))

    return belief


def updateWumpusBeliefs(belief, wumpusAlive):
    if not wumpusAlive:
        for pos in allCells():
            belief[pos]["wumpusProb"] = 0.0
        return belief

    candidates = []
    for pos in allCells():
        if belief[pos]["visited"]:
            belief[pos]["wumpusProb"] = 0.0
            continue

        visitedNbs = [nb for nb in adjCells(*pos) if belief[nb]["visited"]]
        if not visitedNbs:
            continue

        if any(belief[nb]["stench"] is False for nb in visitedNbs):
            belief[pos]["wumpusProb"] = 0.0
        else:
            candidates.append(pos)

    if candidates:
        prob = 1.0 / len(candidates)
        for pos in allCells():
            belief[pos]["wumpusProb"] = prob if pos in candidates else 0.0

    return belief


def updateBelief(belief, r, c, breeze, stench, wumpusAlive):
    belief[(r, c)]["visited"]    = True
    belief[(r, c)]["breeze"]     = breeze
    belief[(r, c)]["stench"]     = stench
    belief[(r, c)]["pitProb"]    = 0.0
    belief[(r, c)]["wumpusProb"] = 0.0

    belief = updatePitBeliefs(belief)
    belief = updateWumpusBeliefs(belief, wumpusAlive)
    return belief


def applyArrowKill(belief):
    for pos in allCells():
        belief[pos]["wumpusProb"] = 0.0
    return belief


def buildLog(belief, r, c, breeze, stench, glitter):
    dr, dc = toDisplay(r, c)
    nb = adjCells(r, c)
    lines = [
        f"Entered cell ({dr},{dc})",
        "",
        "Percepts observed:",
        f"  Breeze  = {'TRUE' if breeze else 'FALSE'}",
        f"  Stench  = {'TRUE' if stench else 'FALSE'}",
        f"  Glitter = {'TRUE' if glitter else 'FALSE'}",
        "",
        "Bayesian update — agent survived entry:",
        f"  P(pit   | ({dr},{dc})) = 0.000  (survived)",
        f"  P(wumpus| ({dr},{dc})) = 0.000  (survived)",
        "",
    ]

    if not breeze:
        lines.append(f"  No breeze at ({dr},{dc}) => sensor model: no adjacent pit")
        lines.append(f"  NOT B => NOT P for all neighbors")
        for nr, nc in nb:
            anr, anc = toDisplay(nr, nc)
            lines.append(f"      P(pit | ({anr},{anc})) = 0.000  [eliminated]")
    else:
        lines.append(f"  Breeze at ({dr},{dc}) => Bayesian update per neighbor:")
        lines.append(f"  Formula: P(pit|B) = 1.0 * P(pit) / P(B)")
        lines.append(f"           P(B) = 1 - (1-P(pit_C)) * q")
        lines.append(f"           q = product(1-P(pit_n)) for other unknown neighbors")
        for nr, nc in nb:
            anr, anc = toDisplay(nr, nc)
            cell = belief[(nr, nc)]
            prob = cell["pitProb"]
            if not cell["visited"]:
                otherNbs = [x for x in adjCells(r, c) if x != (nr, nc) and not belief[x]["visited"]]
                q = 1.0
                for x in otherNbs:
                    q *= (1.0 - belief[x]["pitProb"])
                pB = 1.0 - (1.0 - PRIOR_PIT) * q
                lines.append(f"      ({anr},{anc}): q={q:.3f}  P(B)={pB:.3f}  posterior={prob:.3f}")
            else:
                lines.append(f"      ({anr},{anc}): visited => P(pit)=0.000")

    lines.append("")
    if not stench:
        lines.append(f"  No stench => P(wumpus) = 0 for all neighbours of ({dr},{dc}):")
        for nr, nc in nb:
            anr, anc = toDisplay(nr, nc)
            lines.append(f"      P(wumpus | ({anr},{anc})) = 0.000")
    else:
        lines.append(f"  Stench detected => updating wumpus probs for neighbours:")
        for nr, nc in nb:
            anr, anc = toDisplay(nr, nc)
            prob = belief[(nr, nc)]["wumpusProb"]
            lines.append(f"      P(wumpus | ({anr},{anc})) = {prob:.3f}")

    lines.append("")
    safeCells = sorted([toDisplay(rr, cc) for rr, cc in allCells() if isSafe(belief, (rr, cc))])
    lines.append(f"Cells below safety threshold ({SAFE_THRESHOLD}):")
    lines.append(f"  Safe cells: {safeCells}")
    return lines


def buildArrowLog(direction, hit, wumpusDispPos):
    lines = [
        f"Arrow fired: {direction}",
        f"  Arrow used — haveArrow = FALSE",
        f"  Score -= 10",
        "",
    ]
    if hit:
        wr, wc = wumpusDispPos
        lines += [
            "  Scream heard!",
            "  WumpusAlive = FALSE",
            "  Bayesian update: P(wumpus) = 0.000 for ALL cells",
            f"  Wumpus confirmed was at ({wr},{wc})",
        ]
    else:
        lines += [
            "  No scream. Arrow missed.",
            "  WumpusAlive = TRUE (still at large)",
            "  Wumpus probs remain unchanged",
        ]
    return lines


def initAgent(start):
    dr, dc = toDisplay(*start)
    return {
        "pos":      start,
        "alive":    True,
        "won":      False,
        "hasGold":  False,
        "hasArrow": True,
        "steps":    0,
        "score":    0,
        "status":   "ok",
        "msg":      f"Agent at ({dr},{dc}). Start cell sensed.",
        "log":      [],
    }


def isKnownDangerous(belief, pos):
    return belief[pos]["pitProb"] > 0.85 or belief[pos]["wumpusProb"] > 0.85


def handleMove(agent, world, belief, direction):
    if not agent["alive"] or agent["won"]:
        return agent, belief

    r, c = agent["pos"]
    dr, dc = MOVE_DELTA[direction]
    nr, nc = r + dr, c + dc

    if not (0 <= nr < GRID and 0 <= nc < GRID):
        agent["msg"]    = "Wall. Cannot move in that direction."
        agent["status"] = "warning"
        return agent, belief

    dispR, dispC = toDisplay(nr, nc)

    if isKnownDangerous(belief, (nr, nc)):
        pitP  = belief[(nr, nc)]["pitProb"]
        wumpP = belief[(nr, nc)]["wumpusProb"]
        agent["msg"] = (
            f"Bayesian KB: P(pit)={pitP:.2f}, P(wumpus)={wumpP:.2f} "
            f"at ({dispR},{dispC}). Move blocked (too risky)."
        )
        agent["status"] = "warning"
        return agent, belief

    agent["pos"]    = (nr, nc)
    agent["steps"] += 1
    agent["score"] -= 1

    if (nr, nc) in world["pits"]:
        agent["alive"]  = False
        agent["score"] -= 1000
        agent["msg"]    = f"Fell into pit at ({dispR},{dispC}). Score: {agent['score']}"
        agent["status"] = "danger"
        return agent, belief

    if world["wumpusAlive"] and (nr, nc) == world["wumpus"]:
        agent["alive"]  = False
        agent["score"] -= 1000
        agent["msg"]    = f"Walked into Wumpus at ({dispR},{dispC}). Score: {agent['score']}"
        agent["status"] = "danger"
        return agent, belief

    breeze, stench, glitter = perceiveAt(world, nr, nc)
    belief = updateBelief(belief, nr, nc, breeze, stench, world["wumpusAlive"])
    agent["log"] = buildLog(belief, nr, nc, breeze, stench, glitter)

    parts = []
    if breeze:  parts.append("Breeze")
    if stench:  parts.append("Stench")
    if glitter: parts.append("Glitter -- gold here")

    if glitter:
        agent["hasGold"] = True
        agent["won"]     = True
        agent["score"]  += 1000
        agent["status"]  = "success"
        parts.append(f"Gold collected. Score: {agent['score']}")
    else:
        agent["status"] = "warning" if (breeze or stench) else "ok"

    agent["msg"] = f"Moved {direction} to ({dispR},{dispC}).  {' | '.join(parts) if parts else 'No percepts.'}"
    return agent, belief


def arrowPath(agentPos, direction):
    r, c = agentPos
    dr, dc = MOVE_DELTA[direction]
    path, nr, nc = [], r + dr, c + dc
    while 0 <= nr < GRID and 0 <= nc < GRID:
        path.append((nr, nc))
        nr += dr
        nc += dc
    return path


def handleArrow(agent, world, belief, direction):
    if not agent["hasArrow"]:
        agent["msg"]    = "No arrow remaining."
        agent["status"] = "warning"
        return agent, world, belief

    agent["hasArrow"]  = False
    agent["score"]    -= 10
    path  = arrowPath(agent["pos"], direction)
    hit   = world["wumpusAlive"] and (world["wumpus"] in path)
    wDisp = toDisplay(*world["wumpus"])

    if hit:
        world["wumpusAlive"] = False
        belief = applyArrowKill(belief)
        agent["msg"]    = f"Arrow {direction}. Scream! Wumpus eliminated. Score: {agent['score']}"
        agent["status"] = "success"
    else:
        agent["msg"]    = f"Arrow {direction}. No hit -- arrow wasted. Score: {agent['score']}"
        agent["status"] = "warning"

    agent["log"] = buildArrowLog(direction, hit, wDisp)
    return agent, world, belief


CELL_BG = {
    "agent":          "#D0E8F8",
    "dead":           "#F5D0D0",
    "won":            "#FDE8C0",
    "visited_clear":  "#D4EDDA",
    "visited_warn":   "#FEF3CD",
    "risky":          "#FAEBD7",
    "safe_unvisited": "#EBF5EB",
    "unknown":        "#F0EFED",
}
CELL_BORDER = {
    "agent":          "#5A9FD4",
    "dead":           "#C05050",
    "won":            "#D49030",
    "visited_clear":  "#74B883",
    "visited_warn":   "#D4A017",
    "risky":          "#C5714A",
    "safe_unvisited": "#A5D6A7",
    "unknown":        "#C4C1BC",
}
CELL_TEXT = {
    "agent":          "#0B3D6B",
    "dead":           "#6B1010",
    "won":            "#6B3A08",
    "visited_clear":  "#1A5232",
    "visited_warn":   "#614002",
    "risky":          "#5C2308",
    "safe_unvisited": "#256029",
    "unknown":        "#555250",
}


def classifyCell(pos, world, agent, belief):
    cell    = belief[pos]
    isAgent = (pos == agent["pos"])

    if not agent["alive"] and isAgent: return "dead"
    if agent["won"] and isAgent:       return "won"
    if isAgent:                        return "agent"
    if cell["visited"]:
        return "visited_warn" if (cell["breeze"] or cell["stench"]) else "visited_clear"

    hasWarningNeighbor = any(
        belief[nb]["visited"] and (belief[nb]["breeze"] or belief[nb]["stench"])
        for nb in adjCells(*pos)
    )
    if hasWarningNeighbor:   return "risky"
    if isSafe(belief, pos):  return "safe_unvisited"
    return "unknown"


def getCellLabels(pos, world, agent, belief, revealAll):
    cell    = belief[pos]
    isAgent = (pos == agent["pos"])
    labels  = []

    if isAgent:
        labels.append("Agent")
    if revealAll:
        if pos in world["pits"]:
            labels.append("Pit")
        if pos == world["wumpus"]:
            labels.append("Wumpus" if world["wumpusAlive"] else "Wumpus(dead)")
        if pos == world["gold"] and not agent["hasGold"]:
            labels = ["Gold"]

    if cell["visited"]:
        if cell["breeze"]:  labels.append("Breeze")
        if cell["stench"]:  labels.append("Stench")
        if not labels and not isAgent:
            labels.append("Visited")
    elif not isAgent:
        labels.append(f"P(pit)={cell['pitProb']:.2f}")
        labels.append(f"P(w)={cell['wumpusProb']:.2f}")

    return labels


def renderCell(pos, world, agent, belief, revealAll):
    state     = classifyCell(pos, world, agent, belief)
    bg        = CELL_BG[state]
    border    = CELL_BORDER[state]
    textColor = CELL_TEXT[state]
    labels    = getCellLabels(pos, world, agent, belief, revealAll)
    isAgent   = (pos == agent["pos"])
    isStart   = (pos == world["start"])

    if agent["hasGold"] and pos == world["gold"]:
        labels = ["Gold Collected"]

    dr, dc    = toDisplay(*pos)
    bodyText  = "<br>".join(labels) if labels else "&nbsp;"
    boxShadow = "box-shadow:0 0 0 2px #5A9FD4,0 0 8px rgba(90,159,212,0.3);" if isAgent else ""
    startBadge = (
        "<span style='position:absolute;top:5px;right:7px;font-size:9px;opacity:0.4;letter-spacing:0.04em'>start</span>"
        if isStart else ""
    )

    st.markdown(
        f"<div style='background:{bg};border:1.5px solid {border};border-radius:10px;"
        f"padding:10px 6px;min-height:90px;display:flex;flex-direction:column;"
        f"align-items:center;justify-content:center;position:relative;text-align:center;{boxShadow}'>"
        f"{startBadge}"
        f"<div style='position:absolute;top:6px;left:8px;font-size:10px;color:{textColor};opacity:0.45;font-family:monospace'>({dr},{dc})</div>"
        f"<div style='font-size:12.5px;font-weight:500;color:{textColor};margin-top:8px;line-height:1.45'>{bodyText}</div>"
        f"</div>",
        unsafe_allow_html=True
    )


def renderGrid(world, agent, belief, revealAll):
    for dispRow in range(GRID):
        cols = st.columns(4, gap="small")
        for dispCol in range(GRID):
            with cols[dispCol]:
                renderCell(toInternal(dispRow, dispCol), world, agent, belief, revealAll)


def renderSidebar(world, agent, belief):
    st.markdown("#### Agent Status")

    dr, dc   = toDisplay(*agent["pos"])
    sDr, sDc = toDisplay(*world["start"])

    for label, value in [
        ("Position",   f"({dr}, {dc})"),
        ("Start cell", f"({sDr}, {sDc})"),
        ("State",      "Dead" if not agent["alive"] else ("Won" if agent["won"] else "Active")),
        ("Steps",      str(agent["steps"])),
        ("Score",      str(agent["score"])),
        ("Arrow",      "Available" if agent["hasArrow"] else "Used"),
        ("Wumpus",     "Eliminated" if not world["wumpusAlive"] else "At large"),
        ("Gold",       "Collected" if agent["hasGold"] else "Not found"),
    ]:
        c1, c2 = st.columns([1.2, 1])
        c1.markdown(f"<span style='font-size:12px;opacity:0.5'>{label}</span>", unsafe_allow_html=True)
        c2.markdown(f"<span style='font-size:12px;font-family:monospace;font-weight:500'>{value}</span>", unsafe_allow_html=True)

    st.divider()

    st.markdown("#### Move Agent")
    _, uC, _ = st.columns([1, 2, 1])
    uC.button("Up",    key="mv_up",    use_container_width=True)
    lC, mC, rC = st.columns(3)
    lC.button("Left",  key="mv_left",  use_container_width=True)
    mC.button("Reset", key="reset",    use_container_width=True)
    rC.button("Right", key="mv_right", use_container_width=True)
    _, dC, _ = st.columns([1, 2, 1])
    dC.button("Down",  key="mv_down",  use_container_width=True)

    st.divider()

    if agent["hasArrow"] and agent["alive"] and not agent["won"]:
        st.markdown("#### Fire Arrow  (-10 pts)")
        if belief[agent["pos"]].get("stench"):
            st.caption("Stench at current cell -- wumpus is adjacent.")
        else:
            st.caption("Arrow travels entire row or column until wall.")
        _, auC, _ = st.columns([1, 2, 1])
        auC.button("Fire Up",    key="ar_up",    use_container_width=True)
        alC, _, arC = st.columns(3)
        alC.button("Fire Left",  key="ar_left",  use_container_width=True)
        arC.button("Fire Right", key="ar_right", use_container_width=True)
        _, adC, _ = st.columns([1, 2, 1])
        adC.button("Fire Down",  key="ar_down",  use_container_width=True)
        st.divider()

    st.markdown("#### Legend")
    for bg, border, label in [
        (CELL_BG["agent"],          CELL_BORDER["agent"],          "Agent -- current position"),
        (CELL_BG["visited_clear"],  CELL_BORDER["visited_clear"],  "Visited -- no percept"),
        (CELL_BG["visited_warn"],   CELL_BORDER["visited_warn"],   "Visited -- breeze or stench"),
        (CELL_BG["risky"],          CELL_BORDER["risky"],          "Risky -- elevated probability"),
        (CELL_BG["safe_unvisited"], CELL_BORDER["safe_unvisited"], f"Safe -- below {SAFE_THRESHOLD} threshold"),
        (CELL_BG["dead"],           CELL_BORDER["dead"],           "Dead / Pit"),
        (CELL_BG["won"],            CELL_BORDER["won"],            "Gold collected"),
        (CELL_BG["unknown"],        CELL_BORDER["unknown"],        "Unknown"),
    ]:
        swC, lblC = st.columns([0.3, 2.5])
        swC.markdown(
            f"<div style='width:14px;height:14px;background:{bg};border:1.5px solid {border};border-radius:3px;margin-top:3px'></div>",
            unsafe_allow_html=True
        )
        lblC.markdown(f"<span style='font-size:12px'>{label}</span>", unsafe_allow_html=True)

    st.divider()
    st.markdown("""
#### Scoring
| Event | Points |
|---|---|
| Each move | -1 |
| Fire arrow | -10 |
| Collect gold | +1000 |
| Die | -1000 |
""")


def renderKBExpander(belief):
    with st.expander("Full Belief State -- all 16 cells"):
        st.markdown(
            f"P(pit) and P(wumpus) updated each step via Bayes. Safe threshold = {SAFE_THRESHOLD}."
        )
        st.text(f"{'Cell':>6}  {'P(pit)':^10} {'P(wumpus)':^11} {'Breeze':^8} {'Stench':^8} {'Safe':^8} visited")
        st.text("-" * 72)
        for dRow in range(GRID):
            for dCol in range(GRID):
                pos = toInternal(dRow, dCol)
                d   = belief[pos]
                st.text(
                    f"({dRow},{dCol})   "
                    f"P(pit)={d['pitProb']:.3f}    "
                    f"P(w)={d['wumpusProb']:.3f}    "
                    f"B={str(d['breeze']):<7} "
                    f"S={str(d['stench']):<7} "
                    f"Safe={str(isSafe(belief, pos)):<6} "
                    f"{d['visited']}"
                )


def main():
    st.set_page_config(
        page_title="Wumpus World -- Bayesian Agent",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.markdown("""
    <style>
    .block-container { padding-top: 1.6rem !important; padding-bottom: 2rem !important; }
    .stButton > button {
        font-size: 13px !important; font-weight: 500 !important;
        border-radius: 7px !important;
        border: 1px solid rgba(100,100,100,0.25) !important;
        background: transparent !important; color: inherit !important;
        padding: 0.35rem 0.6rem !important;
        transition: background 0.12s, border-color 0.12s !important;
    }
    .stButton > button:hover {
        background: rgba(100,100,100,0.08) !important;
        border-color: rgba(100,100,100,0.4) !important;
    }
    .stDivider { margin: 10px 0 !important; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.25rem; }
    </style>
    """, unsafe_allow_html=True)

    if "world" not in st.session_state:
        world  = buildWorld()
        start  = world["start"]
        belief = initBelief(start)
        agent  = initAgent(start)
        br, st_, gl = perceiveAt(world, *start)
        belief = updateBelief(belief, *start, br, st_, world["wumpusAlive"])
        agent["log"] = buildLog(belief, *start, br, st_, gl)
        if br or st_:
            parts = (["Breeze"] if br else []) + (["Stench"] if st_ else [])
            dr, dc = toDisplay(*start)
            agent["msg"]    = f"Start cell ({dr},{dc}): {' | '.join(parts)} detected."
            agent["status"] = "warning"
        st.session_state.world  = world
        st.session_state.belief = belief
        st.session_state.agent  = agent

    world  = st.session_state.world
    belief = st.session_state.belief
    agent  = st.session_state.agent

    st.markdown(
        "<h2 style='margin-bottom:2px'>Wumpus World -- Bayesian Agent</h2>"
        "<p style='font-size:13px;opacity:0.4;margin-top:0;margin-bottom:12px'>"
        f"4 x 4 grid &nbsp;&middot;&nbsp; Random world on each reset "
        f"&nbsp;&middot;&nbsp; Bayesian probabilistic inference"
        f"&nbsp;&middot;&nbsp; Safe threshold = {SAFE_THRESHOLD}</p>",
        unsafe_allow_html=True
    )

    gridCol, panelCol = st.columns([2.6, 1], gap="large")

    with gridCol:
        revealAll = st.checkbox("Reveal world (cheat mode -- shows actual pits, Wumpus, Gold)", value=False)
        st.markdown("")
        renderGrid(world, agent, belief, revealAll)

        st.markdown("")
        statusColors = {
            "ok":      ("rgba(40,100,200,0.07)",  "rgba(40,100,200,0.25)",  "#183880"),
            "warning": ("rgba(190,130,20,0.07)",  "rgba(190,130,20,0.25)",  "#6B4800"),
            "danger":  ("rgba(185,50,50,0.07)",   "rgba(185,50,50,0.25)",   "#7A1A1A"),
            "success": ("rgba(30,130,70,0.07)",   "rgba(30,130,70,0.25)",   "#1A5A30"),
        }
        sBg, sBorder, sText = statusColors.get(agent["status"], statusColors["ok"])
        st.markdown(
            f"<div style='padding:10px 14px;border-radius:8px;font-size:13px;line-height:1.5;"
            f"border:0.5px solid {sBorder};background:{sBg};color:{sText};margin-top:4px'>"
            f"{agent['msg']}</div>",
            unsafe_allow_html=True
        )

        st.markdown("")
        st.markdown(
            "<p style='font-size:10px;font-weight:600;letter-spacing:0.08em;"
            "text-transform:uppercase;opacity:0.4;margin-bottom:4px'>"
            "Bayesian inference log -- last step</p>",
            unsafe_allow_html=True
        )
        st.code("\n".join(agent["log"]) if agent["log"] else "No inference recorded yet.", language=None)

    with panelCol:
        renderSidebar(world, agent, belief)

    if st.session_state.get("reset"):
        for k in ["world", "belief", "agent"]:
            del st.session_state[k]
        st.rerun()

    for key, direction in [("mv_up","UP"),("mv_down","DOWN"),("mv_left","LEFT"),("mv_right","RIGHT")]:
        if st.session_state.get(key):
            st.session_state.agent, st.session_state.belief = handleMove(agent, world, belief, direction)
            st.rerun()

    for key, direction in [("ar_up","UP"),("ar_down","DOWN"),("ar_left","LEFT"),("ar_right","RIGHT")]:
        if st.session_state.get(key):
            st.session_state.agent, st.session_state.world, st.session_state.belief = handleArrow(
                agent, world, belief, direction
            )
            st.rerun()

    renderKBExpander(belief)


main()