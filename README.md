# SegmentChain Simulator

A Python simulator that models the **segment blockchain** storage idea from:

> Yibin Xu and Yangyu Huang, *"Segment blockchain: A size reduced storage
> mechanism for blockchain"*, IEEE Access, 2020.

---

## What it does

Instead of every node storing the full chain, SegmentChain:

1. Cuts the block history into **segments** (named slices S1, S2, …).
2. Assigns each segment to **m** random nodes (replicas).
3. Every node still stores all block **headers** and the latest **state**,
   so it can verify any segment it downloads.
4. Measures and visualises the storage savings and the risk of losing a
   segment when nodes fail.

This is a **simulator** — nodes are Python objects, not real computers.
See the Deep Dive guide for a full comparison of what is real vs simulated.

---

## Project structure

```
blockchain.py        Builds the fake chain; verify_chain()
state_machine.py     Account balances and checkpoints
segmentation.py      Cuts blocks into segments
assignment.py        Creates nodes; assigns segment replicas
storage_metrics.py   Byte-count calculations
availability.py      Simulates node failures
probability.py       Paper's formula P = (A/n)^m
integrity.py         Tamper-detection experiments
export.py            Save results to JSON and CSV
app.py               Streamlit dashboard (8 pages)
requirements.txt     pip dependencies
```

---

## Quick start

```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate it
#    Windows:
venv\Scripts\activate
#    macOS / Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the dashboard
streamlit run app.py
```

The browser opens automatically at `http://localhost:8501`.

---

## Default parameters (seed 7)

| Parameter | Value |
|-----------|-------|
| Blocks | 100 |
| Transactions / block | 5 |
| Segments | 5 |
| Nodes | 30 |
| Replicas per segment | 3 |
| Header size | 160 B |
| State size | 4 096 B |
| Block data size | 1 000 B |

With these defaults:

| Storage | Bytes |
|---------|-------|
| Full node | 120 096 B |
| Avg segmented node | 30 096 B |
| **Saving** | **74.9 %** |

---

## Segment assignment (seed 7)

| Segment | Blocks | Stored on |
|---------|--------|-----------|
| S1 | 0–19 | N11, N5, N13 |
| S2 | 20–39 | N21, N2, N3 |
| S3 | 40–59 | N27, N18, N4 |
| S4 | 60–79 | N12, N19, N2 |
| S5 | 80–99 | N30, N17, N7 |

---

## Dashboard pages

| Page | What it shows |
|------|---------------|
| Dashboard | Key metrics, storage bar chart, block samples |
| Segments | Partition table, replica assignment |
| Storage | Per-node bytes, histogram, saving-vs-replicas curve |
| Network | Node grid with segment badges, interactive failure toggle |
| Availability | Random failure simulation, sweep chart |
| Probability | Paper formula, exact formula, multi-curve log chart |
| Integrity | Tamper experiments on a chain copy |
| Export | Save JSON / CSV files to disk |

---

## Known limitations (from the original project)

- No cryptographic signatures on transactions.
- Balances may go negative (no balance check).
- Transactions use a simple SHA-256 over the full list, not a Merkle tree.
- No consensus (mining / staking) — blocks are generated in a loop.
- Segment fetching is not simulated; only "is any copy online?" is checked.
- Storage sizes are model constants, not real measured data.

---

## Source

Xu, Y. and Huang, Y. (2020). *Segment blockchain: A size reduced storage
mechanism for blockchain*. **IEEE Access**, 8, pp. 17 434–17 441.
