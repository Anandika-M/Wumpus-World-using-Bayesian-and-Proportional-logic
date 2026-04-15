import streamlit as st
import random

GRID = 4
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
        if random.random() < 0.2:
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


def initKB(start):
    kb = {}
    for pos in allCells():
        kb[pos] = {
            "P": None,
            "W": None,
            "B": None,
            "S": None,
            "OK": False,
            "visited": False
        }
    kb[start]["P"]  = False
    kb[start]["W"]  = False
    kb[start]["OK"] = True
    return kb


def perceiveAt(world, r, c):
    nb      = adjCells(r, c)
    breeze  = any(n in world["pits"] for n in nb)
    stench  = world["wumpusAlive"] and any(n == world["wumpus"] for n in nb)
    glitter = ((r, c) == world["gold"])
    return breeze, stench, glitter


def runInference(kb, r, c, breeze, stench):
    kb[(r, c)]["visited"] = True
    kb[(r, c)]["B"]       = breeze
    kb[(r, c)]["S"]       = stench
    kb[(r, c)]["P"]       = False
    kb[(r, c)]["W"]       = False
    kb[(r, c)]["OK"]      = True

    nb = adjCells(r, c)
    if not breeze:
        for n in nb:
            if kb[n]["P"] is None:
                kb[n]["P"] = False
    if not stench:
        for n in nb:
            if kb[n]["W"] is None:
                kb[n]["W"] = False
    for pos in allCells():
        if kb[pos]["P"] == False and kb[pos]["W"] == False:
            kb[pos]["OK"] = True
    return kb


def applyArrowKill(kb):
    for pos in allCells():
        kb[pos]["W"] = False
    for pos in allCells():
        if kb[pos]["P"] == False and kb[pos]["W"] == False:
            kb[pos]["OK"] = True
    return kb


def arrowPath(agentPos, direction):
    r, c = agentPos
    dr, dc = MOVE_DELTA[direction]
    path, nr, nc = [], r + dr, c + dc
    while 0 <= nr < GRID and 0 <= nc < GRID:
        path.append((nr, nc))
        nr += dr
        nc += dc
    return path


def buildLog(kb, r, c, breeze, stench, glitter):
    dr, dc = toDisplay(r, c)
    nb     = adjCells(r, c)
    lines  = []
    lines.append(f"Entered cell ({dr},{dc})")
    lines.append("")
    lines.append("Percepts observed:")
    lines.append(f"  B({dr},{dc}) = {'TRUE' if breeze else 'FALSE'}   (breeze?)")
    lines.append(f"  S({dr},{dc}) = {'TRUE' if stench else 'FALSE'}   (stench?)")
    lines.append(f"  Glitter = {'TRUE' if glitter else 'FALSE'}   (gold visible?)")
    lines.append("")
    lines.append("Axioms applied:")
    lines.append(f"  P({dr},{dc}) = FALSE   (survived entry)")
    lines.append(f"  W({dr},{dc}) = FALSE   (survived entry)")
    lines.append(f"  OK({dr},{dc}) = TRUE   (R4: NOT P AND NOT W)")
    lines.append("")
    if not breeze:
        lines.append(f"  R5: NOT B({dr},{dc})  =>")
        for nr, nc in nb:
            anr, anc = toDisplay(nr, nc)
            lines.append(f"      P({anr},{anc}) = FALSE")
    else:
        lines.append(f"  R2: B({dr},{dc}) = TRUE  =>")
        for nr, nc in nb:
            anr, anc = toDisplay(nr, nc)
            if not kb[(nr, nc)]["visited"]:
                lines.append(f"      ({anr},{anc}) = POSSIBLE DANGER")
    lines.append("")
    if not stench:
        lines.append(f"  R6: NOT S({dr},{dc})  =>")
        for nr, nc in nb:
            anr, anc = toDisplay(nr, nc)
            lines.append(f"      W({anr},{anc}) = FALSE")
    else:
        lines.append(f"  R3: S({dr},{dc}) = TRUE  =>")
        for nr, nc in nb:
            anr, anc = toDisplay(nr, nc)
            if not kb[(nr, nc)]["visited"]:
                lines.append(f"      ({anr},{anc}) = POSSIBLE DANGER")
    lines.append("")
    safe = sorted([toDisplay(rr, cc) for rr, cc in allCells() if kb[(rr, cc)]["OK"]])
    lines.append(f"Proven safe cells: {safe}")
    return lines


def buildArrowLog(direction, hit, wumpusDispPos):
    lines = []
    lines.append(f"Arrow fired: {direction}")
    lines.append(f"  HaveArrow(t) = FALSE")
    lines.append(f"  Score -= 10")
    lines.append("")
    if hit:
        wr, wc = wumpusDispPos
        lines.append("  Scream heard!")
        lines.append("  WumpusAlive(t) = FALSE")
        lines.append("  R7: W(r,c) = FALSE for ALL cells")
        lines.append("  OK re-derived across entire KB")
        lines.append(f"  Wumpus was at ({wr},{wc})")
    else:
        lines.append("  No scream. Arrow missed.")
        lines.append("  WumpusAlive(t) = TRUE (still alive)")
    return lines


def initAgent(start):
    dr, dc = toDisplay(*start)
    return {
        "pos": start,
        "alive": True, "won": False,
        "hasGold": False, "hasArrow": True,
        "steps": 0, "score": 0,
        "status": "ok",
        "msg": f"Agent at ({dr},{dc}). Start cell sensed.",
        "log": []
    }


def handleMove(agent, world, kb, direction):
    if not agent["alive"] or agent["won"]:
        return agent, kb

    r, c   = agent["pos"]
    dr, dc = MOVE_DELTA[direction]
    nr, nc = r + dr, c + dc

    if not (0 <= nr < GRID and 0 <= nc < GRID):
        agent["msg"]    = "Wall. Cannot move in that direction."
        agent["status"] = "warning"
        return agent, kb

    dispR, dispC = toDisplay(nr, nc)

    if kb[(nr, nc)]["P"] is True:
        agent["msg"]    = f"KB confirms pit at ({dispR},{dispC}). Move blocked."
        agent["status"] = "warning"
        return agent, kb
    if kb[(nr, nc)]["W"] is True:
        agent["msg"]    = f"KB confirms wumpus at ({dispR},{dispC}). Move blocked."
        agent["status"] = "warning"
        return agent, kb

    agent["pos"]    = (nr, nc)
    agent["steps"] += 1
    agent["score"] -= 1

    if (nr, nc) in world["pits"]:
        agent["alive"]  = False
        agent["score"] -= 1000
        agent["msg"]    = f"Fell into pit at ({dispR},{dispC}). Game over. Score: {agent['score']}"
        agent["status"] = "danger"
        return agent, kb

    if world["wumpusAlive"] and (nr, nc) == world["wumpus"]:
        agent["alive"]  = False
        agent["score"] -= 1000
        agent["msg"]    = f"Walked into Wumpus at ({dispR},{dispC}). Game over. Score: {agent['score']}"
        agent["status"] = "danger"
        return agent, kb

    breeze, stench, glitter = perceiveAt(world, nr, nc)
    kb = runInference(kb, nr, nc, breeze, stench)
    agent["log"] = buildLog(kb, nr, nc, breeze, stench, glitter)

    parts = []
    if breeze:  parts.append("Breeze")
    if stench:  parts.append("Stench")
    if glitter: parts.append("Glitter - gold here")

    if glitter:
        agent["hasGold"]  = True
        agent["won"]      = True
        agent["score"]   += 1000
        agent["status"]   = "success"
        parts.append(f"Gold collected. Score: {agent['score']}")
    else:
        agent["status"] = "warning" if (breeze or stench) else "ok"

    suffix = " | ".join(parts) if parts else "No percepts."
    agent["msg"] = f"Moved {direction} to ({dispR},{dispC}).  {suffix}"
    return agent, kb


def handleArrow(agent, world, kb, direction):
    if not agent["hasArrow"]:
        agent["msg"]    = "No arrow remaining."
        agent["status"] = "warning"
        return agent, world, kb

    agent["hasArrow"]  = False
    agent["score"]    -= 10
    path = arrowPath(agent["pos"], direction)
    hit  = world["wumpusAlive"] and (world["wumpus"] in path)
    wDisp = toDisplay(*world["wumpus"])

    if hit:
        world["wumpusAlive"] = False
        kb = applyArrowKill(kb)
        agent["msg"]    = f"Arrow {direction}. Scream! Wumpus eliminated. Score: {agent['score']}"
        agent["status"] = "success"
    else:
        agent["msg"]    = f"Arrow {direction}. No hit - arrow wasted. Score: {agent['score']}"
        agent["status"] = "warning"

    agent["log"] = buildArrowLog(direction, hit, wDisp)
    return agent, world, kb


#  CELL CLASSIFICATION 

CELL_BG = {
    "agent":           "#D0E8F8",
    "dead":            "#F5D0D0",
    "won":             "#FDE8C0",
    "visited_clear":   "#D4EDDA",
    "visited_warn":    "#FEF3CD",
    "possible_danger": "#FAEBD7",
    "safe_unvisited":  "#EBF5EB",
    "unknown":         "#F0EFED",
}

CELL_BORDER = {
    "agent":           "#5A9FD4",
    "dead":            "#C05050",
    "won":             "#D49030",
    "visited_clear":   "#74B883",
    "visited_warn":    "#D4A017",
    "possible_danger": "#C5714A",
    "safe_unvisited":  "#A5D6A7",
    "unknown":         "#C4C1BC",
}

CELL_TEXT = {
    "agent":           "#0B3D6B",
    "dead":            "#6B1010",
    "won":             "#6B3A08",
    "visited_clear":   "#1A5232",
    "visited_warn":    "#614002",
    "possible_danger": "#5C2308",
    "safe_unvisited":  "#256029",
    "unknown":         "#555250",
}


def classifyCell(pos, world, agent, kb):
    cell    = kb[pos]
    isAgent = (pos == agent["pos"])

    if not agent["alive"] and isAgent:
        return "dead"
    if agent["won"] and isAgent:
        return "won"
    if isAgent:
        return "agent"
    if cell["visited"]:
        return "visited_warn" if (cell["B"] or cell["S"]) else "visited_clear"
    if cell["OK"]:
        return "safe_unvisited"

    for nb in adjCells(*pos):
        if kb[nb]["visited"] and (kb[nb]["B"] or kb[nb]["S"]):
            return "possible_danger"

    return "unknown"


def getCellLabels(pos, world, agent, kb, revealAll):
    cell    = kb[pos]
    isAgent = (pos == agent["pos"])
    labels  = []

    if isAgent:
        labels.append("Agent")

    if revealAll:
        if pos in world["pits"]:
            labels.append("Pit")
        if pos == world["wumpus"]:
            labels.append("Wumpus" if world["wumpusAlive"] else "Wumpus (dead)")
        if pos == world["gold"] and not agent["hasGold"]:
            labels=["Gold"]
        

    if cell["visited"]:
        if cell["B"]:
            labels.append("Breeze")
        if cell["S"]:
            labels.append("Stench")
        if not labels and not isAgent:
            labels.append("Visited")
    elif not isAgent:
        state = classifyCell(pos, world, agent, kb)
        if state == "possible_danger":
            labels.append("Possible Danger")
        elif state == "safe_unvisited":
            labels.append("Safe")
        else:
            labels.append("Unknown")

    return labels


def renderCell(pos, world, agent, kb, revealAll):
    state     = classifyCell(pos, world, agent, kb)
    bg        = CELL_BG[state]
    border    = CELL_BORDER[state]
    textColor = CELL_TEXT[state]
    labels    = getCellLabels(pos, world, agent, kb, revealAll)
    isAgent   = (pos == agent["pos"])
    isStart   = (pos == world["start"])
    if agent["hasGold"] and pos == world["gold"]:
        labels = ["Gold Collected"]

    dr, dc = toDisplay(*pos)
    coordLine = f"({dr},{dc})"

    bodyText = "<br>".join(labels) if labels else "&nbsp;"

    boxShadow = "box-shadow:0 0 0 2px #5A9FD4,0 0 8px rgba(90,159,212,0.3);" if isAgent else ""

    startBadge = (
        "<span style='position:absolute;top:5px;right:7px;"
        "font-size:9px;opacity:0.4;letter-spacing:0.04em;'>start</span>"
        if isStart else ""
    )

    html = (
        f"<div style='"
        f"background:{bg};"
        f"border:1.5px solid {border};"
        f"border-radius:10px;"
        f"padding:10px 6px 10px 6px;"
        f"min-height:90px;"
        f"display:flex;flex-direction:column;"
        f"align-items:center;justify-content:center;"
        f"position:relative;"
        f"text-align:center;"
        f"{boxShadow}"
        f"'>"
        f"{startBadge}"
        f"<div style='position:absolute;top:6px;left:8px;"
        f"font-size:10px;color:{textColor};opacity:0.45;"
        f"font-family:monospace;'>{coordLine}</div>"
        f"<div style='font-size:12.5px;font-weight:500;"
        f"color:{textColor};margin-top:8px;line-height:1.45'>"
        f"{bodyText}"
        f"</div>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def renderGrid(world, agent, kb, revealAll):
    for dispRow in range(GRID):
        cols = st.columns(4, gap="small")
        for dispCol in range(GRID):
            intPos = toInternal(dispRow, dispCol)
            with cols[dispCol]:
                renderCell(intPos, world, agent, kb, revealAll)


def renderSidebar(world, agent, kb):
    st.markdown("#### Agent Status")

    dr, dc       = toDisplay(*agent["pos"])
    sDr, sDc     = toDisplay(*world["start"])
    gameState    = "Dead" if not agent["alive"] else ("Won" if agent["won"] else "Active")
    arrowState   = "Available" if agent["hasArrow"] else "Used"
    goldState    = "Collected" if agent["hasGold"] else "Not found"
    wumpusState  = "Eliminated" if not world["wumpusAlive"] else "At large"

    for label, value in [
        ("Position",   f"({dr}, {dc})"),
        ("Start cell", f"({sDr}, {sDc})"),
        ("State",      gameState),
        ("Steps",      str(agent["steps"])),
        ("Score",      str(agent["score"])),
        ("Arrow",      arrowState),
        ("Wumpus",     wumpusState),
        ("Gold",       goldState),
    ]:
        c1, c2 = st.columns([1.2, 1])
        c1.markdown(
            f"<span style='font-size:12px;opacity:0.5'>{label}</span>",
            unsafe_allow_html=True
        )
        c2.markdown(
            f"<span style='font-size:12px;font-family:monospace;font-weight:500'>{value}</span>",
            unsafe_allow_html=True
        )

    st.divider()

    st.markdown("#### Move Agent")
    _, uC, _ = st.columns([1, 2, 1])
    uC.button("Up", key="mv_up", use_container_width=True)
    lC, mC, rC = st.columns(3)
    lC.button("Left",  key="mv_left",  use_container_width=True)
    mC.button("Reset", key="reset",    use_container_width=True)
    rC.button("Right", key="mv_right", use_container_width=True)
    _, dC, _ = st.columns([1, 2, 1])
    dC.button("Down", key="mv_down", use_container_width=True)

    st.divider()

    if agent["hasArrow"] and agent["alive"] and not agent["won"]:
        st.markdown("#### Fire Arrow  (-10 pts)")
        currentS = kb[agent["pos"]].get("S", False)
        if currentS:
            st.caption("Stench active at current cell - wumpus is adjacent.")
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

    legendRows = [
        (CELL_BG["agent"],           CELL_BORDER["agent"],           "Agent - current position"),
        (CELL_BG["visited_clear"],   CELL_BORDER["visited_clear"],   "Visited - no percept"),
        (CELL_BG["visited_warn"],    CELL_BORDER["visited_warn"],    "Visited - breeze or stench"),
        (CELL_BG["possible_danger"], CELL_BORDER["possible_danger"], "Possible danger (inferred)"),
        (CELL_BG["safe_unvisited"],  CELL_BORDER["safe_unvisited"],  "Safe - KB proven, unvisited"),
        (CELL_BG["dead"],            CELL_BORDER["dead"],            "Dead / Pit"),
        (CELL_BG["won"],             CELL_BORDER["won"],             "Gold collected"),
        (CELL_BG["unknown"],         CELL_BORDER["unknown"],         "Unknown"),
    ]

    for bg, border, label in legendRows:
        swC, lblC = st.columns([0.3, 2.5])
        swC.markdown(
            f"<div style='width:14px;height:14px;background:{bg};"
            f"border:1.5px solid {border};border-radius:3px;margin-top:3px'></div>",
            unsafe_allow_html=True
        )
        lblC.markdown(
            f"<span style='font-size:12px'>{label}</span>",
            unsafe_allow_html=True
        )

    st.divider()

    st.markdown("#### Scoring")
    st.markdown(
        """
| Event | Points |
|---|---|
| Each move | -1 |
| Fire arrow | -10 |
| Collect gold | +1000 |
| Die | -1000 |
        """
    )


def main():
    st.set_page_config(
        page_title="Wumpus World - Propositional Logic Agent",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    code, .monospace {
        font-family: 'IBM Plex Mono', monospace !important;
    }
    .block-container {
        padding-top: 1.6rem !important;
        padding-bottom: 2rem !important;
    }
    h1, h2, h3, h4 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.2px !important;
    }
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        border-radius: 7px !important;
        border: 1px solid rgba(100,100,100,0.25) !important;
        background: transparent !important;
        color: inherit !important;
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
        kb     = initKB(start)
        agent  = initAgent(start)
        br, st_, gl = perceiveAt(world, *start)
        kb = runInference(kb, *start, br, st_)
        agent["log"] = buildLog(kb, *start, br, st_, gl)
        if br or st_:
            parts = []
            if br:  parts.append("Breeze")
            if st_: parts.append("Stench")
            dr, dc = toDisplay(*start)
            agent["msg"]    = f"Start cell ({dr},{dc}): {' | '.join(parts)} detected."
            agent["status"] = "warning"
        st.session_state.world = world
        st.session_state.kb    = kb
        st.session_state.agent = agent

    world = st.session_state.world
    kb    = st.session_state.kb
    agent = st.session_state.agent

    st.markdown(
        "<h2 style='margin-bottom:2px'>Wumpus World - Propositional Logic Agent</h2>"
        "<p style='font-size:13px;opacity:0.4;margin-top:0;margin-bottom:12px'>"
        "4 x 4 grid &nbsp;&middot;&nbsp; Random world on each reset "
        "&nbsp;&middot;&nbsp; Propositional logic inference (R1-R7)</p>",
        unsafe_allow_html=True
    )

    gridCol, panelCol = st.columns([2.6, 1], gap="large")

    with gridCol:
        revealAll = st.checkbox(
            "Reveal world (cheat mode - shows actual pits, Wumpus, Gold)",
            value=False
        )
        st.markdown("")
        renderGrid(world, agent, kb, revealAll)

        # Event message
        st.markdown("")
        statusColors = {
            "ok":      ("rgba(40,100,200,0.07)",  "rgba(40,100,200,0.25)",  "#183880"),
            "warning": ("rgba(190,130,20,0.07)",  "rgba(190,130,20,0.25)",  "#6B4800"),
            "danger":  ("rgba(185,50,50,0.07)",   "rgba(185,50,50,0.25)",   "#7A1A1A"),
            "success": ("rgba(30,130,70,0.07)",   "rgba(30,130,70,0.25)",   "#1A5A30"),
        }
        sBg, sBorder, sText = statusColors.get(agent["status"], statusColors["ok"])
        st.markdown(
            f"<div style='padding:10px 14px;border-radius:8px;font-size:13px;"
            f"line-height:1.5;border:0.5px solid {sBorder};"
            f"background:{sBg};color:{sText};margin-top:4px'>"
            f"{agent['msg']}"
            f"</div>",
            unsafe_allow_html=True
        )

        # Inference log
        st.markdown("")
        st.markdown(
            "<p style='font-size:10px;font-weight:600;letter-spacing:0.08em;"
            "text-transform:uppercase;opacity:0.4;margin-bottom:4px'>"
            "Propositional inference log - last step</p>",
            unsafe_allow_html=True
        )
        logText = "\n".join(agent["log"]) if agent["log"] else "No inference recorded yet."
        st.code(logText, language=None)

    with panelCol:
        renderSidebar(world, agent, kb)

    if st.session_state.get("reset"):
        for k in ["world", "kb", "agent"]:
            del st.session_state[k]
        st.rerun()

    for key, direction in [("mv_up","UP"),("mv_down","DOWN"),("mv_left","LEFT"),("mv_right","RIGHT")]:
        if st.session_state.get(key):
            st.session_state.agent, st.session_state.kb = handleMove(agent, world, kb, direction)
            st.rerun()

    for key, direction in [("ar_up","UP"),("ar_down","DOWN"),("ar_left","LEFT"),("ar_right","RIGHT")]:
        if st.session_state.get(key):
            st.session_state.agent, st.session_state.world, st.session_state.kb = handleArrow(
                agent, world, kb, direction
            )
            st.rerun()

    with st.expander("Full Knowledge Base - all 16 cells"):
        st.markdown(
            "Each cell shows the agent's current belief: "
            "`P` = pit belief, `W` = wumpus belief, `B` = breeze, `S` = stench, "
            "`OK` = proven safe, `visited` = agent has been here."
        )
        header = f"{'Cell':>6}  {'P(pit)':^10} {'W(wumpus)':^11} {'B':^7} {'S':^7} {'OK':^8} visited"
        st.text(header)
        st.text("─" * 68)
        for dRow in range(GRID):
            for dCol in range(GRID):
                pos = toInternal(dRow, dCol)
                d   = kb[pos]
                st.text(
                    f"({dRow},{dCol})   "
                    f"P={str(d['P']):<9} "
                    f"W={str(d['W']):<10} "
                    f"B={str(d['B']):<6} "
                    f"S={str(d['S']):<6} "
                    f"OK={str(d['OK']):<7} "
                    f"{d['visited']}"
                )


main()