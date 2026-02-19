# GKG Vault Schema & Graph Topology

## Overview
- **Total .md files**: ~2,557 (714 in LO/, 1,843 in SAQ/)
- **Entity types**: SAQ (1,672), lo (557), index (314), concept (5), paper (2), SAQ-Index (2), no entityType (3)
- **Wikilink graph**: 2,873 unique targets, 37,579 total references

## Folder Structure
```
gkg/
├── LO/
│   ├── ANZCA/          (sections A-Y, each a curriculum domain)
│   │   ├── A_applied-procedural-anatomy/
│   │   ├── B_fundamental-pharmacology/
│   │   │   ├── B1_pharmacodynamics/
│   │   │   └── B2_pharmacokinetics/
│   │   ├── ... (through Y_generic-overarching-principles)
│   │   └── ANZCA.md (index)
│   └── CICM/
│       ├── CORE/
│       └── NON_CORE/
├── SAQ/
│   └── ANZCA/
│       ├── AP00A/ through AP25B/ (166 paper folders)
│       └── Each contains individual question files
├── TaskNotes/
├── _types/
└── heartbeat.md
```

## Entity Type: `lo` (Learning Objective) — 557 files

### Core Fields (present in 555-557 files)
| Field | Count | Example Value |
|-------|-------|---------------|
| `entityType` | 557 | `lo` |
| `college` | 557 | `ANZCA` |
| `title` | 557 | `APViv_basic-physics` |
| `aliases` | 557 | `['BT_SQ 1.5', 'APViv', ...]` |
| `summary` | 557 | Full text of the learning objective |
| `description` | 557 | Same as summary (duplicated) |
| `variation` | 557 | (variation category) |
| `section.code` | 557 | (section code) |
| `Title` | 557 | (display title) |
| `section` | 556 | `[[V_physics-and-clinical-measurement]]` (wikilink to index) |
| `section.sub` | 556 | `[[]]` or wikilink to subsection |
| `topic` | 556 | `PRINCIPLES OF PHYSICS` |
| `action` | 556 | (verb/action type) |
| `type.measurement` | 556 | (measurement classification) |
| `sectionanzca` | 556 | (ANZCA section mapping) |
| `sectionanzcatopic` | 556 | (ANZCA topic mapping) |
| `topicdepth` | 556 | (depth of topic) |
| `sectiondomaincode` | 556 | (domain code) |
| `sectiondomain` | 556 | (domain name) |
| `section.sub.code` | 556 | (subsection code) |
| `complexity` | 555 | (complexity level) |

### Cross-Reference Fields
| Field | Count | Description |
|-------|-------|-------------|
| `lo.mapped` | 533 | Mapped learning objectives |
| `saq.direct` | 312 | Direct SAQ links, e.g. `['[[AP23B14]]', '[[AP11A16]]', ...]` |

### Rare/Specialized Fields (13-14 files — likely CICM LOs)
| Field | Count |
|-------|-------|
| `section.sub.sub.code` | 14 |
| `id` | 13 |
| `exam` | 13 |
| `college.anzca` | 13 |
| `topic.sub` | 13 |
| `type.physiology` | 13 |
| `type.pharmacology` | 13 |
| `type.anatomy` | 13 |
| `college.cicm` | 13 |

### Pharmacopeia Fields (8-11 files)
| Field | Count |
|-------|-------|
| `pharmacopeia.level3` | 11 |
| `pharmacopeia.level1` | 10 |
| `pharmacopeia.level2` | 9 |

### Variation Fields (7-8 files)
| Field | Count |
|-------|-------|
| `variation.pregnancy` | 8 |
| `variation.anaesthesia` | 8 |
| `variation.neonatal` | 7 |

### Verb Fields (sparse)
| Field | Count |
|-------|-------|
| `verb.outline` | 7 |
| `elo.indirect` | 8 |

## Entity Type: `SAQ` — 1,672 files

### Core Fields (present in 1,647-1,672 files)
| Field | Count | Example Value |
|-------|-------|---------------|
| `entityType` | 1,672 | `SAQ` |
| `title` | 1,671 | Full question text |
| `exam` | 1,671 | `PEX` |
| `college` | 1,671 | `ANZCA` |
| `year` | 1,671 | `2002` |
| `sitting` | 1,671 | `A` or `B` |
| `question` | 1,671 | `11` (question number) |
| `Title` | 1,650 | `[[AP02A11\|AP02A11]]` (wikilink) |
| `passRate` | 1,647 | `77` (percentage) |

### Examiner Comment Fields
| Field | Count | Description |
|-------|-------|-------------|
| `ec.expected` | 1,542 | Expected answer content (list of strings) |
| `ec.errors` | 1,476 | Common errors (list of strings) |
| `ec.extra` | 1,322 | Extra credit points (list of strings) |
| `EC_expectedDomains` | 22 | (alternate format) |
| `EC_extraCredit` | 21 | (alternate format) |
| `EC_errorsCommon` | 14 | (alternate format) |

### Cross-Reference Fields
| Field | Count | Description |
|-------|-------|-------------|
| `lo.direct` | 855 | Direct LO links, e.g. `['[[APF1i]]', '[[APD1iii]]']` |
| `saq.direct` | 838 | Related SAQs (direct) |
| `saq.indirect` | 835 | Related SAQs (indirect) |
| `elo.indirect` | 558 | Indirect extended LO links |
| `resources` | 233 | Resource links |
| `lo` | 167 | (alternate LO field) |
| `lo.indirect` | 1 | (rare) |

### Graph Metrics (43 files)
| Field | Count |
|-------|-------|
| `in_degree` | 43 |
| `out_degree` | 43 |
| `pagerank` | 43 |
| `eigenvector_centrality` | 43 |
| `cluster_id` | 43 |
| `staleness_days` | 43 |

### Other Fields
| Field | Count |
|-------|-------|
| `summary` | 35 |
| `section.letter` | 16 |
| `histogram` | 15 |

## Entity Type: `index` — 314 files

### Fields
| Field | Count | Example |
|-------|-------|----------|
| `entityType` | 314 | `index` |
| `Title` | 314 | `[[V_physics-and-clinical-measurement\|V_physics-and-clinical-measurement]]` |
| `in_degree` | 15 | (graph metric) |
| `out_degree` | 15 | (graph metric) |
| `pagerank` | 15 | (graph metric) |
| `eigenvector_centrality` | 15 | (graph metric) |
| `cluster_id` | 15 | (graph metric) |
| `staleness_days` | 15 | (graph metric) |

Body typically contains Waypoint-generated directory listings.

## Entity Type: `concept` — 5 files
Same schema as `lo` (all LO fields present). Located within LO folders.

## Entity Type: `paper` — 2 files
(Parse errors on some — complex YAML with embedded quotes)

## Special Files
- `heartbeat.md`: Plugin health monitor (last_beat, status, obsidian_version, vault_files, vault_size_mb, uptime_hours, api_status)
- `distribution.md`: Graph metrics only

## Wikilink Graph Topology

### Stats
- **2,873 unique link targets**
- **37,579 total link references**

### Top 30 Most-Linked Targets
All top targets are "AP99" synthetic/aggregate SAQ nodes:

| Target | Inbound Links | Likely Meaning |
|--------|--------------|----------------|
| AP99A05 | 742 | Aggregate topic node |
| AP99A11 | 702 | Aggregate topic node |
| AP99A04 | 545 | Aggregate topic node |
| AP99A07 | 544 | Aggregate topic node |
| AP99A08 | 544 | Aggregate topic node |
| AP99A03 | 520 | Aggregate topic node |
| AP99A02 | 519 | Aggregate topic node |
| AP99A01 | 518 | Aggregate topic node |
| AP99A06 | 518 | Aggregate topic node |
| AP99A13 | 454 | Aggregate topic node |
| AP99A16 | 419 | Aggregate topic node |
| AP99A10 | 412 | Aggregate topic node |
| AP99A09 | 375 | Aggregate topic node |
| AP99B02 | 361 | Aggregate topic node |
| AP99B08 | 311 | Aggregate topic node |
| AP99A12 | 297 | Aggregate topic node |
| AP99B04 | 273 | Aggregate topic node |
| AP99B11 | 265 | Aggregate topic node |
| AP99B12 | 240 | Aggregate topic node |
| AP99A14 | 239 | Aggregate topic node |
| AP99B10 | 220 | Aggregate topic node |
| AP99A15 | 213 | Aggregate topic node |
| AP99B06 | 206 | Aggregate topic node |
| AP99B13 | 204 | Aggregate topic node |
| AP99B01 | 180 | Aggregate topic node |
| AP99B14 | 111 | Aggregate topic node |
| AP20A04 | 109 | Real SAQ |
| AP99B03 | 102 | Aggregate topic node |
| AP99B16 | 99 | Aggregate topic node |
| AP23A02 | 99 | Real SAQ |

The AP99* nodes appear to be synthetic/topic-aggregate SAQ nodes that many real SAQs link to via `saq.direct` and `saq.indirect` fields.

## Key Relationship Patterns

1. **LO → SAQ** via `saq.direct` field on LO files (312 LOs have this)
2. **SAQ → LO** via `lo.direct` field on SAQ files (855 SAQs have this)
3. **SAQ → SAQ** via `saq.direct` (838) and `saq.indirect` (835) fields
4. **SAQ → LO** via `elo.indirect` field (558 SAQs) — extended/indirect LO mapping
5. **Index files** serve as navigation hubs with Waypoint-generated directory listings
6. **AP99* nodes** are heavily-linked synthetic aggregate/topic nodes
