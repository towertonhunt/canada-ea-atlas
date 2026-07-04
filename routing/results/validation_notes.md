# Wawa-Timmins Routing Validation — v0 Results

Reproduction of the Hydro One / Dillon routing study (June 2025) using only
public LIO data and open methods. Benchmark: 9 professional routes, avg 293.4 km.

| Metric | Dillon (avg of 9) | Our V1 | Delta |
|---|---|---|---|
| Route length | 293.4 km | 322.6 km | +10% |
| Parallels existing transmission | Segments A & C predominantly | 72% of length within ~1.5 km | consistent |
| Parallels roads (Hwy 101 role) | Segment B variably | 47% of length | consistent |
| Avoids FN reserves + Game Preserve area | FB (forbidden) | FB honoured (+14,000) | same rule |

Alternatives V2 (391.7 km) and V3 (319.2 km) show the same divergence pattern
as Dillon's B1-B5 family once the primary corridor is penalized.

v0 limitations: no terrain (12% weight unallocated), no CLUPA / mining claims /
railways layers (endpoint title mismatches), 300 m cells, rankings transcribed
from report prose rather than their Appendix C table. Each is mechanical to fix.

Conclusion: public data + open least-cost-path methods reproduce the core
behaviour of a professional MCDM routing study. The expensive, irreplaceable
part of the real process is the consultation that shapes the framework — which
is exactly where a live-rerun tool adds value in the room.
