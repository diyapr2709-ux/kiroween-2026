"""The walker: a MINERVA-style policy over cards, without an LSTM (ADR-001 D2).

State at step t: the query relation r_q, the current entity e_t, and the history h_t = mean of
the relation embeddings taken so far. Query vector q_t = R[r_q] + h_t. Each available action is
a card (r, e') leaving e_t, plus NO_OP (stay). Its score is

    s(a) = <q_t, R[r_a]> + <q_t, E[e_a]>

and the policy is softmax over the available actions. Because s is bilinear, every gradient is
closed-form (numpy only):  ds/dR[r_a] = q,  ds/dE[e_a] = q,  ds/dq = R[r_a] + E[e_a],  and q
distributes to R[r_q] and to each history relation with weight 1/t.

Two training modes on the same parameters:
  rl  — REINFORCE with a moving-average baseline, entropy bonus, and action dropout (Lin et
        al. 2018): terminal reward 1 if the walk ends on the gold entity.
  sl  — supervised: for each training fact, mask its own card (and inverse), BFS the shortest
        card path within T in the remaining graph, and train the policy to take that path with
        cross-entropy (teacher forcing). Facts with no alternative path contribute nothing.
Decoding: beam search (B = 64) over T steps; an entity's score is its best path log-prob; the
best path is returned as the deck of cards for the answer. Deterministic under a seed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .baselines import Ranker
from .code_table import INVERSE
from .deck import Fact
from .graph import NO_OP, Graph

NOOP_FACT = None  # sentinel action


@dataclass
class WalkResult:
    answer: str | None
    path: list[Fact]
    log_prob: float
    step_probs: list[float]


class Policy(Ranker):
    def __init__(self, mode: str = "rl", hops: int = 4, dim: int = 32, epochs: int = 40, rollouts: int = 20,
                 lr: float = 0.05, entropy: float = 0.02, action_dropout: float = 0.1, beam: int = 64,
                 baseline_decay: float = 0.9, verbose: bool = False) -> None:
        if mode not in ("rl", "sl"):
            raise ValueError("mode must be 'rl' or 'sl'")
        self.mode, self.hops, self.dim, self.epochs, self.rollouts = mode, hops, dim, epochs, rollouts
        self.lr, self.entropy, self.action_dropout, self.beam = lr, entropy, action_dropout, beam
        self.baseline_decay, self.verbose = baseline_decay, verbose
        self.name = f"policy_{mode}"
        self.history: list[dict] = []

    # ---- parameters ------------------------------------------------------------------
    def _init(self, graph: Graph, all_entities: list[str], seed: int) -> None:
        self.g = graph
        self.rng = np.random.RandomState(seed)
        self.rels = sorted(set(INVERSE) | {NO_OP})
        self.ridx = {r: i for i, r in enumerate(self.rels)}
        self.ents = sorted(set(all_entities) | set(graph.entities))
        self.eidx = {e: i for i, e in enumerate(self.ents)}
        scale = 1.0 / math.sqrt(self.dim)
        self.R = self.rng.normal(0, scale, (len(self.rels), self.dim))
        self.E = self.rng.normal(0, scale, (len(self.ents), self.dim))
        # Adam state
        self.mR, self.vR = np.zeros_like(self.R), np.zeros_like(self.R)
        self.mE, self.vE = np.zeros_like(self.E), np.zeros_like(self.E)
        self.t_adam = 0
        self.baseline = 0.0

    def _actions(self, e: str, masked: set[tuple[str, str, str]]) -> list[Fact | None]:
        acts: list[Fact | None] = [f for f in self.g.edges(e) if f.triple() not in masked]
        acts.append(NOOP_FACT)
        return acts

    def _features(self, acts: list[Fact | None], e_cur: str):
        ri = np.array([self.ridx[NO_OP] if a is None else self.ridx[a.relation] for a in acts])
        ei = np.array([self.eidx[e_cur] if a is None else self.eidx[a.object] for a in acts])
        return ri, ei

    def _scores(self, q: np.ndarray, ri: np.ndarray, ei: np.ndarray) -> np.ndarray:
        return self.R[ri] @ q + self.E[ei] @ q

    @staticmethod
    def _softmax(s: np.ndarray) -> np.ndarray:
        z = s - s.max()
        p = np.exp(z)
        return p / p.sum()

    # ---- one episode's gradient contribution -----------------------------------------
    def _accumulate(self, gR: np.ndarray, gE: np.ndarray, steps: list[tuple], weight_fn) -> None:
        """steps: list of (q, ri, ei, probs, chosen, rq_idx, hist_idx_list). Adds ∇ log π(chosen) * w
        plus the entropy-gradient term when weight_fn returns an entropy coefficient."""
        for (q, ri, ei, p, a, rq, hist) in steps:
            w, ent = weight_fn(p)
            # d log π(a) / ds = onehot(a) - p ; entropy term: dH/ds = -p * (log p + H)
            dlogp = -p.copy()
            dlogp[a] += 1.0
            ds = w * dlogp
            if ent:
                H = -(p * np.log(p + 1e-12)).sum()
                ds += ent * (-p * (np.log(p + 1e-12) + H))
            # ds/dR[r_a] = q ; ds/dE[e_a] = q
            np.add.at(gR, ri, np.outer(ds, q))
            np.add.at(gE, ei, np.outer(ds, q))
            # ds/dq = sum_a ds_a (R[r_a] + E[e_a]); q = R[rq] + mean(hist)
            dq = ds @ (self.R[ri] + self.E[ei])
            gR[rq] += dq
            if hist:
                for h in hist:
                    gR[h] += dq / len(hist)

    def _adam(self, gR: np.ndarray, gE: np.ndarray) -> None:
        self.t_adam += 1
        b1, b2, eps = 0.9, 0.999, 1e-8
        for P, g, m, v in ((self.R, gR, self.mR, self.vR), (self.E, gE, self.mE, self.vE)):
            m[:] = b1 * m + (1 - b1) * g
            v[:] = b2 * v + (1 - b2) * g * g
            mhat = m / (1 - b1 ** self.t_adam)
            vhat = v / (1 - b2 ** self.t_adam)
            P += self.lr * mhat / (np.sqrt(vhat) + eps)  # ascent (objective is maximised)

    def _rollout(self, s: str, rq: str, gold: str, masked: set, train: bool) -> tuple[list[tuple], str]:
        e = s
        hist: list[int] = []
        steps = []
        rq_i = self.ridx[rq]
        for _ in range(self.hops):
            acts = self._actions(e, masked)
            ri, ei = self._features(acts, e)
            q = self.R[rq_i] + (self.R[hist].mean(axis=0) if hist else 0.0)
            sc = self._scores(q, ri, ei)
            if train and self.action_dropout > 0 and len(acts) > 1:
                keep = self.rng.rand(len(acts)) >= self.action_dropout
                keep[-1] = True  # NO_OP always available
                sc = np.where(keep, sc, -1e9)
            p = self._softmax(sc)
            a = int(self.rng.choice(len(acts), p=p)) if train else int(p.argmax())
            steps.append((q, ri, ei, p, a, rq_i, list(hist)))
            act = acts[a]
            if act is not None:
                hist.append(self.ridx[act.relation])
                e = act.object
        return steps, e

    def _masked(self, s: str, r: str, o: str) -> set[tuple[str, str, str]]:
        return {(s, r, o), (o, INVERSE[r], s)}

    # ---- training ----------------------------------------------------------------------
    def fit(self, graph: Graph, train_facts: list[Fact], val_facts: list[Fact], seed: int) -> None:
        all_entities = {f.subject for f in train_facts + val_facts} | {f.object for f in train_facts + val_facts}
        self._init(graph, sorted(all_entities), seed)
        queries = []
        for f in train_facts:
            queries.append((f.subject, f.relation, f.object))
            queries.append((f.object, INVERSE[f.relation], f.subject))
        self.history = []
        if self.mode == "sl":
            self._fit_sl(queries, val_facts)
        else:
            self._fit_rl(queries, val_facts)

    def _fit_sl(self, queries, val_facts) -> None:
        # Teacher paths, computed once: BFS in the graph with the query's own card masked.
        demos = []
        for s, r, o in queries:
            masked = self._masked(s, r, o)
            path = _bfs_masked(self.g, s, o, self.hops, masked)
            if path:
                demos.append((s, r, o, path))
        self.n_demos = len(demos)
        for ep in range(self.epochs):
            order = self.rng.permutation(len(demos))
            gR, gE = np.zeros_like(self.R), np.zeros_like(self.E)
            loss = 0.0
            for i in order:
                s, r, o, path = demos[i]
                masked = self._masked(s, r, o)
                e, hist, steps = s, [], []
                rq_i = self.ridx[r]
                targets = list(path) + [None] * (self.hops - len(path))
                for tgt in targets:
                    acts = self._actions(e, masked)
                    ri, ei = self._features(acts, e)
                    q = self.R[rq_i] + (self.R[hist].mean(axis=0) if hist else 0.0)
                    p = self._softmax(self._scores(q, ri, ei))
                    a = len(acts) - 1 if tgt is None else next(k for k, x in enumerate(acts) if x is not None and x.triple() == tgt.triple())
                    steps.append((q, ri, ei, p, a, rq_i, list(hist)))
                    loss -= math.log(p[a] + 1e-12)
                    if tgt is not None:
                        hist.append(self.ridx[tgt.relation])
                        e = tgt.object
                self._accumulate(gR, gE, steps, lambda p: (1.0, 0.0))
            n = max(1, len(demos))
            self._adam(gR / n, gE / n)
            rec = {"epoch": ep, "loss": loss / n}
            if val_facts and (ep % 10 == 9 or ep == self.epochs - 1):
                rec["val_hits1"] = self._val_hits1(val_facts)
            self.history.append(rec)
            if self.verbose:
                print(rec)

    def _fit_rl(self, queries, val_facts) -> None:
        for ep in range(self.epochs):
            order = self.rng.permutation(len(queries))
            gR, gE = np.zeros_like(self.R), np.zeros_like(self.E)
            total_r = 0.0
            n_ep = 0
            for i in order:
                s, r, o = queries[i]
                masked = self._masked(s, r, o)
                for _ in range(self.rollouts):
                    steps, end = self._rollout(s, r, o, masked, train=True)
                    reward = 1.0 if end == o else 0.0
                    adv = reward - self.baseline
                    self.baseline = self.baseline_decay * self.baseline + (1 - self.baseline_decay) * reward
                    self._accumulate(gR, gE, steps, lambda p, adv=adv: (adv, self.entropy))
                    total_r += reward
                    n_ep += 1
            self._adam(gR / max(1, n_ep), gE / max(1, n_ep))
            rec = {"epoch": ep, "train_reward": total_r / max(1, n_ep), "baseline": self.baseline}
            if val_facts and (ep % 10 == 9 or ep == self.epochs - 1):
                rec["val_hits1"] = self._val_hits1(val_facts)
            self.history.append(rec)
            if self.verbose:
                print(rec)

    def _val_hits1(self, val_facts: list[Fact]) -> float:
        hits = 0
        n = 0
        for f in val_facts:
            for s, r, o in ((f.subject, f.relation, f.object), (f.object, INVERSE[f.relation], f.subject)):
                res = self.walk(s, r, masked=self._masked(s, r, o))
                hits += int(res.answer == o)
                n += 1
        return hits / n if n else 0.0

    # ---- decoding ----------------------------------------------------------------------
    def beam_search(self, s: str, rq: str, masked: set | None = None) -> list[tuple[str, float, list[Fact], list[float]]]:
        """Returns (entity, best log-prob, path, step probs) for every entity reached, best first."""
        masked = masked or set()
        if s not in self.g.index or rq not in self.ridx:
            return []
        rq_i = self.ridx[rq]
        beams: list[tuple[float, str, list[int], list[Fact], list[float]]] = [(0.0, s, [], [], [])]
        for _ in range(self.hops):
            cand = []
            for lp, e, hist, path, probs in beams:
                acts = self._actions(e, masked)
                ri, ei = self._features(acts, e)
                q = self.R[rq_i] + (self.R[hist].mean(axis=0) if hist else 0.0)
                p = self._softmax(self._scores(q, ri, ei))
                for k, a in enumerate(acts):
                    if a is None:
                        cand.append((lp + math.log(p[k] + 1e-12), e, hist, path, probs + [float(p[k])]))
                    else:
                        cand.append((lp + math.log(p[k] + 1e-12), a.object, hist + [self.ridx[a.relation]], path + [a], probs + [float(p[k])]))
            cand.sort(key=lambda x: -x[0])
            beams = cand[: self.beam]
        best: dict[str, tuple[float, list[Fact], list[float]]] = {}
        for lp, e, _, path, probs in beams:
            if e == s:
                continue  # the query entity is never an answer (staying put, or looping back)
            if e not in best or lp > best[e][0]:
                best[e] = (lp, path, probs)
        return sorted(((e, lp, path, probs) for e, (lp, path, probs) in best.items()), key=lambda x: -x[1])

    def scores(self, subject: str, relation: str) -> dict[str, float]:
        return {e: lp for e, lp, _, _ in self.beam_search(subject, relation)}

    def walk(self, subject: str, relation: str, masked: set | None = None) -> WalkResult:
        res = self.beam_search(subject, relation, masked)
        if not res:
            return WalkResult(None, [], -math.inf, [])
        e, lp, path, probs = res[0]
        return WalkResult(e, path, lp, probs)


def _bfs_masked(g: Graph, start: str, goal: str, hops: int, masked: set) -> list[Fact] | None:
    from collections import deque
    if start not in g.index or goal not in g.index or start == goal:
        return None
    prev: dict[str, Fact] = {}
    seen = {start}
    frontier = deque([(start, 0)])
    while frontier:
        e, d = frontier.popleft()
        if d == hops:
            continue
        for f in g.edges(e):
            if f.triple() in masked or f.object in seen:
                continue
            seen.add(f.object)
            prev[f.object] = f
            if f.object == goal:
                path, cur = [], goal
                while cur != start:
                    path.append(prev[cur])
                    cur = prev[cur].subject
                return path[::-1]
            frontier.append((f.object, d + 1))
    return None
