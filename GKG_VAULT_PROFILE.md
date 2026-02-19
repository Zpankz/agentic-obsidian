# GKG Vault Structural Profile

Generated: 2025-02-19

## 1. Overview

| Metric | Value |
|--------|-------|
| Total files | ~2,570 (2,561 .md + 8 .base + 1 .gitignore) |
| LO files (Learning Outcomes) | 714 .md |
| SAQ files (Short Answer Questions) | 1,843 .md |
| Root-level files | 3 (AGENTS.md, distribution.md, heartbeat.md) |
| _types definitions | 1 (task.md) |
| .base database configs | 8 (lo.base, saq.base, + 6 TaskNotes views) |
| Vault size | ~180 MB |
| Colleges | 2: ANZCA (anaesthesia) and CICM (critical care) |

## 2. Directory Tree

```
gkg/
├── AGENTS.md                  # Agent instructions (bd issue tracker)
├── distribution.md            # SAQ topic distribution quotas
├── heartbeat.md               # Obsidian health monitor
├── _types/
│   └── task.md                # TaskNotes type schema (mdbase-spec v0.2.0)
├── TaskNotes/
│   └── Views/                 # 6 .base files (kanban, calendar, agenda, etc.)
├── LO/
│   ├── lo.base                # Obsidian Properties DB config for LOs
│   ├── ANZCA/                 # 25 sections (A_ through Y_)
│   │   ├── A_applied-procedural-anatomy/
│   │   │   ├── A1_airway-respiratory/
│   │   │   ├── A2_vascular-access/
│   │   │   └── A3_neuraxial/
│   │   ├── B_fundamental-pharmacology/
│   │   │   ├── B1_pharmacodynamics/
│   │   │   ├── B2_pharmacokinetics/
│   │   │   └── B3_variability-in-drug-response/
│   │   ├── ... (C_ through Y_)
│   │   └── Y_generic-overarching-principles/
│   └── CICM/
│       ├── CORE/
│       │   ├── C_respiratory-system/ (56 files)
│       │   ├── D_cardiovascular-system/ (43 files)
│       │   ├── EFG_renal-fluids-elecs/ (35 files)
│       │   └── HI_neuro-muscular/ (48 files)
│       └── NON_CORE/
│           ├── ABQ_cellular-pharmacophysiology/ (31 files)
│           ├── JKM_gastro-hepato-nutritional-metabolism/ (45 files)
│           ├── LP_endo-obs/ (30 files)
│           └── NO_haem-immuno-micro/ (32 files)
└── SAQ/
    ├── saq.base               # Obsidian Properties DB config for SAQs
    ├── ANZCA/                 # 54 sittings (AP99A-AP25B)
    │   ├── AP99A/             # 16 questions (early format)
    │   ├── AP00A/             # 16 questions
    │   ├── ...                # AP00B through AP12B: 16 questions each
    │   ├── AP13A/             # 15 questions (format change)
    │   ├── AP13C/             # 16 questions (special sitting)
    │   ├── ...                # AP13B through AP25B: 15 questions each
    │   └── AP25B/
    └── CICM/                  # 37 sittings (CP07B-CP25B)
        ├── CP07B/             # 24 questions (early format)
        ├── ...                # CP07B-CP17B: 24 questions each
        ├── CP18A/             # 20 questions (format change)
        ├── ...                # CP18A-CP25B: 20 questions each
        ├── CP24A/             # Has AM/PM subdirectories
        │   ├── CP24A-AM/      # Morning session questions
        │   └── CP24A-PM/      # Afternoon session questions
        └── CP25B/
```

## 3. Entity Types

The vault uses `entityType` in frontmatter to distinguish note types:

| entityType | Count | Description |
|-----------|-------|-------------|
| `lo` | ~562 | Learning Outcome notes (leaf content) |
| `SAQ` | ~1,676 | Short Answer Question notes |
| `index` | ~315 | Navigation/index notes (Waypoint-managed) |

## 4. LO (Learning Outcome) Frontmatter Schema

### Core Fields (present on ~561 LOs)
```yaml
entityType: lo                              # Always "lo"
college: ANZCA|CICM                         # Source college
title: APE1i_anatomy-lungs                  # Unique LO identifier
aliases:                                    # Alternative references
  - BT_PO 1.7                               # Original syllabus code
  - APE1i                                   # Short code
  - ANZCA_5_1_1_BT_PO_1_7_...              # Long canonical form
summary: "..."                              # Brief summary
description: "..."                          # Full description text
section: "[[E_respiratory-system]]"         # Wikilink to parent section
section.sub: "[[E1_respiratory-anatomy]]"   # Wikilink to subsection
section.sub.sub: (optional)                 # Sub-subsection link
section.code: 5                             # Numeric/letter section code
section.sub.code: 1                         # Numeric subsection code
section.sub.sub.code: (optional)            # Sub-sub code
sectionanzca: "5.a"                         # ANZCA syllabus reference
sectionanzcatopic: FUNCTIONAL ANATOMY       # ANZCA topic name
sectiondomain: Physiology                   # Domain (Physiology/etc)
sectiondomaincode: PO                       # Domain abbreviation
topic: FUNCTIONAL ANATOMY                   # Topic category
topicdepth: 2                               # Hierarchy depth
action: Outline|Describe|Explain|Compare... # Bloom's verb
complexity: 1.0-3.0                         # Numeric complexity
type.measurement: true|false                # Subject flags
variation: General                          # Variation type
lo.mapped: "[[CPC1i]]"                      # Cross-college mapping (wikilink)
Title: "[[APE1i_anatomy-lungs|...]]"        # Self-referencing wikilink
```

### Relationship Fields (LOs)
```yaml
saq.direct:                                 # Direct SAQ references
  - "[[AP17A01]]"
  - "[[AP13A08]]"
```

### Enriched Fields (present on ~7-13 LOs, likely pilot batch)
```yaml
# Boolean subject-type flags
type.physiology: false
type.pharmacology: true
type.anatomy: false
college.anzca: true
college.cicm: false

# Boolean verb flags
verb.outline: true
verb.define: false
verb.list: false
verb.classify: false
verb.describe-explain: false
verb.compare-contrast: false
verb.examples: true

# Boolean variation flags  
variation.neonatal: false
variation.obesity: true
variation.elderly: false
variation.pregnancy: false
variation.illness: true
variation.anaesthesia: true
variation.sex: false
variation.genetic: false

# Additional hierarchical info
topic.sub: RESPIRATORY PHARMACOLOGY
topic.sub.sub: BT_PO 1.41
id: APE3iii
exam: true                                  # Boolean (not PEX string)
```

## 5. SAQ Frontmatter Schema

### Core Fields (~1,676 SAQs)
```yaml
entityType: SAQ                             # Always "SAQ"
college: ANZCA|CICM                         # Source college
title: "Question text..."                   # Full question text
summary: "Brief summary..."                 # (on ~597 SAQs)
exam: PEX                                   # Exam type (always PEX)
year: 2025                                  # Integer year
sitting: A|B|C                              # Sitting letter
question: 1                                 # Question number (integer)
passRate: 56                                # Pass rate percentage (integer)
```

### Examiner Comment Fields
```yaml
ec.expected:                                # Expected knowledge (on ~1,542)
  - "Domain 1 description"
  - "Domain 2 description"
ec.errors:                                  # Common errors (on ~1,476)
  - "Error description"
ec.extra:                                   # Extra credit topics (on ~1,322)
  - "Extra credit description"
```

### Relationship Fields (SAQs)
```yaml
lo.direct:                                  # Direct LO links (on ~859)
  - "[[APG2iv]]"
  - "[[APG2v]]"
elo.indirect:                               # Cross-college LO links (on ~568)
  - "[[CPD3vi|CPD3vi]]"
saq.direct:                                 # Related SAQs - direct (on ~1,156)
  - "[[AP99A05]]"
saq.indirect:                               # Related SAQs - indirect (on ~837)
  - "[[AP99A01]]"
```

### Additional SAQ Fields
```yaml
histogram:                                  # Score distribution (on ~15 SAQs)
  "0": 2
  "1": 28
  "2": 82
  "3": 103
  "4": 35
  "5": 4
resources:                                  # Study resources (on ~233 SAQs)
  - "resource reference"
section.letter:                             # CICM section ref (on ~16)
  - "[[Aiii_cellular-receptors|CICM.A.iii]]"

# Legacy fields (older format, ~17-32 SAQs)
EC_expectedDomains: ...                     # Older examiner comment format
EC_errorsCommon: ...
EC_extraCredit: ...
```

### Graph Metadata (on ~61 files, mostly recent CICM)
```yaml
in_degree: 2
out_degree: 0
pagerank: 0.001
eigenvector_centrality: 0
cluster_id: CP24A08
staleness_days: 0
```

## 6. Index Notes Schema

```yaml
---
entityType: index
Title: "[[A1_airway-respiratory|A1_airway-respiratory]]"
---
%% Begin Waypoint %%
- [[APA1i_anatomy-upper]]
- [[APA1ii_anatomy-relevant]]
%% End Waypoint %%
```

Index notes use the Waypoint plugin to auto-generate child lists. Some (recent CICM) also have graph metadata.

## 7. Wikilink Relationship Patterns

### Link Architecture

1. **LO → Section hierarchy**: `section`, `section.sub`, `section.sub.sub` fields contain wikilinks to index notes
2. **LO → SAQ**: `saq.direct` field contains wikilinks to directly related SAQ notes
3. **SAQ → LO**: `lo.direct` field contains wikilinks to LO notes the question tests
4. **Cross-college LO mapping**: `lo.mapped` (on LOs) and `elo.indirect` (on SAQs) link ANZCA↔CICM equivalents
5. **SAQ → SAQ**: `saq.direct` and `saq.indirect` link related questions across sittings
6. **Index → children**: Waypoint-managed wikilink lists

### Most Referenced LO Sections (in LO files)
| Count | Target |
|-------|--------|
| 46 | C_respiratory-system (CICM) |
| 45 | E_respiratory-system (ANZCA) |
| 41 | E2_respiratory-physiology |
| 36 | D_cardiovascular-system (CICM) |
| 32 | L_pain |
| 29 | H_nervous-system |
| 27 | G_cardiovascular-system (ANZCA) |

### Most Referenced SAQs (in SAQ files)
The AP99A/AP99B questions (legacy/benchmark) are the most cross-referenced, with AP99A05 appearing in 737 SAQ files' relationship fields. These likely serve as anchor/canonical questions.

## 8. .base Database Configurations

### lo.base (Obsidian Properties plugin)
- **Formulas**: 18 computed fields including:
  - `id`, `sectionPath`, `verbCategory`, `complexityLabel`
  - `hasMappedANZCA`, `mappingConfidence`
  - `relatedLOCount`, `relatedConceptCount`, `relatedSAQCount`
  - `hasVariations`, `topicDepthLabel`, `fullDescription`
- **Property aliases**: Maps internal field names to display names (e.g., `note.measurement` → `type.measurement`)
- **Table view**: Filtered on `file.path.startsWith("LO_linked")` with comprehensive column ordering

### saq.base (Obsidian Properties plugin)
- **Formulas**: 17 computed fields including:
  - `id`, `passRateTier`, `difficulty`
  - `expectedCount`, `errorsCount`, `hasExtra`
  - `examSession`, `questionRef`
  - `totalResponses` (from histogram)
  - `relatedLOCount`, `relatedConceptCount`, `relatedSAQCount`
- **Table view**: Filtered on `file.inFolder("SAQ")` with comprehensive column ordering

### View Schema (both .base files reference)
Both define an extensive set of fields for table display including:
- `related.direct.{LO,concepts,SAQ,VIVA,MCQ}` — direct relationships
- `related.indirect.{LO,concepts,SAQ,VIVA,MCQ}` — indirect relationships
- `related.indirect.FEX.{ANZCA,CICM}.{LO,concepts,SAQ,VIVA,MCQ}` — cross-college FEX
- `concepts.relevance.{anaesthesia,criticalcare}` — clinical relevance

**Note**: Many fields referenced in .base formulas (related.direct.*, related.indirect.*, concepts.*, etc.) are NOT yet present in the actual note frontmatter. They represent the **target schema** for future enrichment.

## 9. _types/task.md Schema

Defines a TaskNotes plugin schema (mdbase-spec v0.2.0) with fields:
- Core: title, status (none/open/in-progress/done), priority (none/low/normal/high)
- Dates: due, scheduled, completedDate, dateCreated, dateModified
- Relations: contexts, projects (wikilinks), blockedBy
- Tracking: timeEstimate, timeEntries, reminders
- Recurrence: recurrence, recurrence_anchor
- Integration: icsEventId, googleCalendarEventId

## 10. Naming Conventions

### LO File Names
- ANZCA: `AP{Section}{Subsection}{Roman}_{slug}.md` → e.g., `APE1i_anatomy-lungs.md`
- CICM: `{Letter}{Number}{Roman}_{slug}.md` → e.g., `H5i_intracranial-pressure-measurement.md`

### SAQ File Names
- ANZCA: `AP{YY}{Sitting}{QQ}.md` → e.g., `AP25A01.md` (2025, sitting A, question 1)
- CICM: `CP{YY}{Sitting}{QQ}.md` → e.g., `CP24A01.md` (2024, sitting A, question 1)
- AP99 = legacy/pre-2000; AP00 = year 2000; AP13C = special third sitting

### Sitting Directories
- ANZCA: `AP{YY}{Sitting}/` with 15-16 question files + 1 index file
- CICM: `CP{YY}{Sitting}/` with 20-24 question files + 1 index; recent sittings have `AM/PM` subdirectories

### Section Directories
- ANZCA: `{Letter}_{kebab-case-name}/` → `E_respiratory-system/`
- CICM CORE: `{Letters}_{kebab-case}/` → `EFG_renal-fluids-elecs/`
- Sub-sections: `{Letter}{Number}_{kebab-case}/` → `E2_respiratory-physiology/`

## 11. SAQ Distribution Rules (from distribution.md)

Each sitting allocates questions by topical quota:
- **CORE 7-11**: C: 2-3, D: 2-3, EFG: 1-2, HI: 2-3
- **NON-CORE 3-8**: AB: 1-2, JKLM: 1-3, NO: 1-2, P: 0-1
- **Pharmacology 3-5**: C-I: 2-3, AB+J-Q: 1-2
- 1-2 anatomy SAQs, 1-2 measurement SAQs

## 12. Data Completeness Summary

| Field Category | Coverage | Notes |
|---------------|----------|-------|
| Core LO fields | 561/562 (~100%) | title, section, action, complexity |
| LO cross-college mapping | 537/562 (96%) | lo.mapped |
| LO → SAQ links | ~variable | saq.direct on most LOs |
| SAQ core fields | 1,676/1,676 (100%) | year, sitting, question, college |
| SAQ pass rates | 1,652/1,676 (99%) | Missing on newest questions |
| SAQ examiner comments | 1,322-1,542 | ec.expected most common |
| SAQ → LO links | 859/1,676 (51%) | ANZCA only; CICM SAQs lack lo.direct |
| SAQ → SAQ links | 1,156/1,676 (69%) | saq.direct |
| Enriched verb/variation booleans | 7-13 (~1%) | Pilot batch only |
| Graph metadata | 61 (~2%) | Recent CICM files only |
| Histogram data | 15 (<1%) | Very recent SAQs only |

## 13. Key Architectural Patterns

1. **Bidirectional linking**: LOs link to SAQs (`saq.direct`) and SAQs link back to LOs (`lo.direct`), creating a queryable exam-to-curriculum graph
2. **Cross-college mapping**: ANZCA and CICM LOs are mapped via `lo.mapped` / `elo.indirect`, enabling cross-college question analysis
3. **Hierarchical taxonomy**: 3-level section hierarchy (section → sub → sub.sub) with both wikilinks and dotted codes
4. **Dual schema**: The .base files define a rich target schema with many fields (related.*, concepts.*, verb.*, variation.*) that are mostly unpopulated — only a pilot batch of ~7-13 files has the full enrichment
5. **Index notes with Waypoint**: Auto-generated navigation using `%% Begin Waypoint %%` markers
6. **Exam sitting as organizational unit**: SAQs grouped by sitting directories with index files
7. **AP99 as benchmark**: AP99A/B SAQs serve as highly cross-referenced anchor points in the relationship graph
