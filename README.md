# Wumpus World: Propositional and Bayesian Agents

## Overview

This project implements the classic Wumpus World problem using two different AI approaches:

- Propositional Logic Agent (deterministic reasoning)
- Bayesian Agent (probabilistic reasoning)

The goal of the agent is to safely navigate a 4x4 grid, avoid pits and the Wumpus, and retrieve the gold.

---

## Features

- Grid-based Wumpus World environment
- Random world generation
- Two reasoning approaches:
  - Rule-based propositional logic
  - Bayesian probabilistic inference
- Real-time belief updates
- Risk-aware decision making
- Visualization using Streamlit

---

## Environment Details

- Grid size: 4 x 4
- Each cell may contain:
  - Pit (probability = 0.2 per cell)
  - Wumpus (exactly one)
  - Gold (exactly one)
- Agent starts in a safe cell

---

## Propositional Logic Agent

### Description

The propositional agent uses logical rules and a knowledge base to infer safe and unsafe cells.

### Key Concepts

- Uses propositional variables:
  - P(i,j): Pit at cell
  - W(i,j): Wumpus at cell
  - B(i,j): Breeze
  - S(i,j): Stench
  - OK(i,j): Safe

### Reasoning

- Based on deterministic rules:
  - No breeze implies no adjacent pits
  - No stench implies no adjacent Wumpus
- Uses logical inference to mark cells as safe or unsafe

### Characteristics

- Deterministic
- Binary decisions (safe or unsafe)
- No uncertainty handling

---

## Bayesian Agent

### Description

The Bayesian agent maintains probabilities for pits and the Wumpus and updates beliefs using observations.

### Key Concepts

- Pit probabilities:
  - Independent per cell
  - Prior: 0.2
- Wumpus probability:
  - Exactly one Wumpus
  - Uniform distribution over candidates

### Reasoning

- Uses Bayes’ theorem to update beliefs:
  - P(H | E) = P(E | H) * P(H) / P(E)
- Observations:
  - Breeze indicates at least one neighboring pit
  - Stench indicates Wumpus in neighboring cells

### Characteristics

- Handles uncertainty
- Produces probabilistic outputs
- Supports risk-based decisions

---

## How It Works

1. Initialize world and agent
2. Agent observes percepts (breeze, stench, glitter)
3. Update knowledge:
   - Logical rules (Propositional)
   - Probability updates (Bayesian)
4. Infer safe moves
5. Move agent
6. Repeat until:
   - Gold is found
   - Agent dies

---

## Running the Project

```bash
streamlit run wumpus_bayesian.py
streamlit run wumpus_propositional.py
