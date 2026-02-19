# Obsidian Bases Deep Dive — Complete Report

## 1. obaq CLI (v1.1.0)

**Package:** `obaq@1.1.0` — BSD-2-Clause — by knu (Akinori Musha)  
**GitHub:** https://github.com/knu/obaq  
**Published:** 2 weeks ago (early Feb 2026)

### Usage

```
obaq [options] (-e YAML | PATH.md)

Options:
  -d, --directory VAULT_DIR   Vault directory (defaults to cwd and auto-detects)
  -e, --eval YAML             YAML query string or @file.base (use @- for stdin)
  -f, --format FORMAT         Output format: json|csv|md|markdown
      --title-width MODE      Table width: markup|title (default: markup)
  -t, --this PATH             Use PATH as the "this" file context
      --version               Show version
  -h, --help                  Show this help
```

### Two Modes of Operation

1. **Query mode** (`-e`): Evaluates a YAML query, outputs structured results
   ```bash
   obaq -d /vault -e '@query.base' -f json
   obaq -d /vault -e 'filters: {and: ["file.inFolder(\"Notes\")"]}' -f csv
   ```

2. **Markdown replacement mode** (`PATH.md`): Replaces ` ```base ` code blocks in markdown with rendered tables
   ```bash
   obaq -d /vault report.md  # Outputs markdown with base blocks replaced by tables
   cat report.md | obaq -     # Read from stdin
   ```

### Exported Node.js API

```typescript
export { parseVault } from "./parser.js";      // parseVault(vaultPath: string): Promise<ObsidianFile[]>
export { executeQuery } from "./query.js";      // executeQuery(files, query, thisContext?): QueryResult
export { evaluateExpression } from "./evaluator.js"; // evaluateExpression(expr, context, this?, vault?)
export { applyFilter } from "./filter.js";      // applyFilter(files, filter, this?, vault?)
export { replaceBaseCodeBlocks } from "./markdown.js"; // Process markdown with base blocks
export { findVaultRoot } from "./vault-finder.js";
```

### Type Definitions (from obaq source)

```typescript
interface BaseQuery {
  filters?: Filter;
  formulas?: Record<string, string>;
  properties?: Record<string, PropertyConfig>;
  views?: View[];
}

interface View {
  type: string;
  name: string;
  filters?: Filter;
  order?: string[];
  sort?: SortConfig[];
  columnSize?: Record<string, number>;
}

type Filter = string | { and: Filter[] } | { or: Filter[] } | { not: Filter[] };

class VaultFile {
  name: string; folder: string; path: string; ext: string;
  size: number; ctime: Date; mtime: Date;
  properties: Record<string, unknown>; tags: string[];
  asLink(title?): Link;
  hasProperty(name): boolean;
  hasTag(...tags): boolean;
  hasLink(...links): boolean;
  inFolder(folder): boolean;
}

interface QueryResult {
  columns: { id: string; displayName: string; size?: number }[];
  rows: Record<string, unknown>[];
}
```

### Built-in Functions (from obaq functions.d.ts)

**Global Functions:**
- `date(input)` — Parse date
- `duration(value)` — Parse duration string
- `if(condition, trueResult, falseResult?)` — Conditional
- `max(...values)`, `min(...values)` — Numeric min/max
- `random()` — Random number
- `link(path, display?)` — Create wiki link
- `list(element)` — Convert to array
- `now()` — Current datetime
- `today()` — Today at midnight
- `number(input)` — Convert to number

**String Extensions:** `.contains()`, `.containsAll()`, `.containsAny()`, `.endsWith()`, `.isEmpty()`, `.lower()`, `.replace()`, `.reverse()`, `.startsWith()`, `.title()`

**Number Extensions:** `.abs()`, `.ceil()`, `.floor()`, `.round(digits?)`, `.isEmpty()`

**Array Extensions:** `.mean()`, `.median()`, `.stddev()`, `.contains()`, `.containsAll()`, `.containsAny()`, `.isEmpty()`, `.flat()`, `.unique()`, `.sort()`

**Date Extensions:** `.date()`, `.format(fmt)`, `.time()`, `.relative()`, `.isEmpty()`

**Object Extensions:** `.isEmpty()`, `.keys()`, `.values()`

**RegExp Extensions:** `.matches(value)`

**Duration Support:** `"1d"`, `"2h"`, `"3w"`, `"1 year"`, `"30m"`, `"45s"`

### Known Limitation

obaq uses strict YAML parsing. If ANY `.md` file in the vault has duplicate frontmatter keys, the entire vault parse fails. It scans all files before filtering.

### Tested Results

```bash
# Successfully queried 561 LO notes (from clean directory without duplicate-key files)
cd /tmp/obaq-lo-test && npx obaq -d . -e '@LO/lo.base' --format json
# -> Columns: 83, Rows: 0 (0 because filter uses file.path.startsWith("LO_linked") but files are in "LO")

# With corrected filter:
npx obaq -d . -e 'filters: {and: ["file.hasProperty(\"sectiondomain\")"]}' --format json
# -> Columns: 3, Rows: 561

# Markdown replacement mode works:
npx obaq -d . test-embedded.md  # Replaces ```base blocks with markdown tables
```

---

## 2. @type32/obsidian-bases-parser (v0.3.0)

**Package:** `@type32/obsidian-bases-parser` — MIT — by Type-32  
**GitHub:** https://github.com/Type-32/obsidian-bases-parser  
**Dependencies:** `vue` ^3.5.27, `js-yaml` ^4.1.1

### API Surface

**This is a library, not a CLI tool.** Key exports:

1. **Schema/Types** — Complete TypeScript definitions for `.base` files
2. **Builder APIs:**
   - `createBase()` — Static builder: `.withFilters()`, `.addFormula()`, `.addTableView()`, `.build()`
   - `createReactiveBase()` — Mutable/reactive builder: `.addFilter()`, `.addFormula()`, `.toYAML()`
3. **Parser:** `parseFilter(expr)` → AST, `parseFilterExpression(expr)` → FilterExpObject with extracted components
4. **Evaluator:** `evaluateFilter(expr, context)` → `{ type: 'BOOLEAN', value: true }`
5. **Validator:** `validateFilter(filterObj)` — Check filter validity
6. **Serializer:** `serializeToYAML(base)` — Convert to .base YAML
7. **Vue Integration:** `useBaseQuery()` composable for reactive queries
8. **Presets:**
   - `PresetFilters.byTag()`, `.byExtension()`, `.inFolder()`, `.modifiedWithin()`, `.byProperty()`
   - `PresetFormulas.daysUntilDue()`, `.isOverdue()`, `.lastModified()`, `.priorityLabel()`, `.statusIcon()`, `.formatCurrency()`
   - `PresetSummaries.customAverage()`, `.countFilled()`, `.percentTrue()`, `.uniqueJoin()`

### View Types Defined

```typescript
TableView:  { type: 'table', sort, columnSize, groupBy, summaries }
CardsView:  { type: 'cards', cardSize, image, imageFit, imageAspectRatio }
ListView:   { type: 'list' }
MapView:    { type: 'map' }  // For obsidian-maps plugin
```

---

## 3. All .base File Contents from Vault

### 3a. `LO/lo.base` — Learning Outcomes Database

```yaml
formulas:
  id: if(title, title, file.name)
  college.anzca: if(college == "ANZCA", true, false)
  college.cicm: if(college == "CICM", true, false)
  sectionPath: section.code + "." + section.sub.code + if(section.sub.sub.code, "." + section.sub.sub.code, "")
  verbCategory: if(action == "Define" || action == "List", "Basic", if(action == "Describe" || action == "Outline" || action == "Explain", "Intermediate", if(action == "Compare" || action == "Contrast" || action == "Discuss", "Advanced", "Other")))
  complexityLabel: if(complexity == 1, "Low", if(complexity == 2, "Medium", if(complexity == 3, "High", "Unknown")))
  type.anatomy: if(anatomy, true, false)
  type.physiology: if(physiology, true, false)
  type.pharmacology: if(pharmacology, true, false)
  type.measurement: if(measurement, true, false)
  hasMappedANZCA: if(mapped1 || mapped2 || mapped3, "Yes", "No")
  mappingConfidence: if(mappedscore >= 0.7, "High", if(mappedscore >= 0.5, "Medium", if(mappedscore > 0, "Low", "None")))
  relatedLOCount: list(related.direct.LO).length + list(related.indirect.LO).length
  relatedConceptCount: list(related.direct.concepts).length + list(related.indirect.concepts).length
  relatedSAQCount: list(related.direct.SAQ).length + list(related.indirect.SAQ).length
  hasDirectRelations: if(list(related.direct.LO).length + list(related.direct.concepts).length + list(related.direct.SAQ).length > 0, "Yes", "No")
  hasCrossCollege: if(list(elo.mapped).length > 0, "Yes", "No")
  hasSAQRefs: if(list(saq.direct).length > 0, "Yes", "No")
  topicDepthLabel: if(topicdepth == 1, "Section", if(topicdepth == 2, "Subsection", if(topicdepth == 3, "Topic", "Root")))
  hasVariations: if(variation_neonatal || variation_elderly || variation_illness || variation_anaesthesia || variation_sex || variation_genetic, "Yes", "No")
  keywordCount: if(keywords, keywords.split(";").length, 0)
  fullDescription: 'action + ": " + description'
properties:
  note.measurement:      { displayName: type.measurement }
  note.exam:             { displayName: exam.pex }
  note.pharmacology:     { displayName: type.pharmacology }
  note.anatomy:          { displayName: type.anatomy }
  note.physiology:       { displayName: type.physiology }
  note.college_cicm:     { displayName: college.cicm }
  note.college_anzca:    { displayName: college.anzca }
  note.sectioncode:      { displayName: section.code }
  note.sectionsubcode:   { displayName: section.sub.code }
  # ... 14 more property display name mappings
views:
  - type: table
    name: Table
    filters:
      and:
        - file.path.startsWith("LO_linked")
        - file.hasProperty("sectiondomain")
    order:  # 83 columns including formulas, note properties, file properties
      - exam
      - formula.id
      - formula.sectionPath
      - description
      - formula.fullDescription
      - formula.verbCategory
      - formula.complexityLabel
      # ... (83 total columns)
    sort:
      - property: verb_define     direction: ASC
      - property: measurement     direction: ASC
      - property: id              direction: ASC
      - property: concepts.relevance  direction: ASC
      - property: college         direction: DESC
    columnSize:
      note.exam: 106
      formula.sectionPath: 261
      note.description: 930
      # ... more column sizes
```

### 3b. `SAQ/saq.base` — SAQ Exam Questions Database

```yaml
formulas:
  id: college + "-" + year + "-" + sitting + "-" + if(question < 10, "0" + question, question)
  passRateTier: if(passRate >= 60, "High (≥60%)", if(passRate >= 40, "Medium (40-59%)", "Low (<40%)"))
  difficulty: if(passRate < 30, "Hard", if(passRate < 50, "Moderate", "Easy"))
  expectedCount: list(ec.expected).length
  errorsCount: list(ec.errors).length
  hasExtra: if(list(ec.extra).length > 0, "Yes", "No")
  college.anzca: if(college == "ANZCA", true, false)
  college.cicm: if(college == "CICM", true, false)
  examSession: year + " " + sitting
  questionRef: college + " " + year + sitting + " Q" + question
  hasLOs: if(list(learningOutcomes).length > 0, "Yes", "No")
  totalResponses: if(histogram, histogram[0]+histogram[1]+histogram[2]+histogram[3]+histogram[4]+histogram[5], 0)
  relatedLOCount: list(related.direct.LO).length + list(related.indirect.LO).length
  hasLODirect: if(list(lo.direct).length > 0, "Yes", "No")
  hasCrossCollege: if(list(elo.indirect).length > 0, "Yes", "No")
  relatedConceptCount: list(related.direct.concepts).length + list(related.indirect.concepts).length
  relatedSAQCount: list(related.direct.SAQ).length + list(related.indirect.SAQ).length
  hasDirectRelations: ...
properties:
  note.title: { displayName: title }
views:
  - type: table
    name: Table
    filters:
      and:
        - file.inFolder("SAQ")
        - file.hasProperty("ec.expected")
    order:  # 67 columns
      - file.name, formula.id, formula.questionRef, college, exam, year, sitting, question,
        title, summary, passRate, formula.passRateTier, formula.difficulty, ...
    sort:
      - property: year        direction: DESC
      - property: file.name   direction: ASC
      - property: college     direction: ASC
    columnSize:
      file.name: 109, formula.id: 156, note.exam: 85, ...
```

### 3c. `TaskNotes/Views/tasks-default.base` — Task Management (6 tabs)

```yaml
filters:
  and:
    - file.hasTag("task")
formulas:  # 40+ formulas for task management
  priorityWeight: 'if(priority=="none",0,if(priority=="low",1,if(priority=="normal",2,if(priority=="high",3,999))))'
  daysUntilDue: 'if(due, ((number(date(due)) - number(today())) / 86400000).floor(), null)'
  isOverdue: 'due && date(due) < today() && status != "done"'
  urgencyScore: 'if(!due && !scheduled, formula.priorityWeight, formula.priorityWeight + max(0, 10 - formula.daysUntilNext))'
  timeTrackedFormatted: 'if(timeEntries, ... complex time tracking ... , "0m")'
  dueDateDisplay: 'if(!due, "", if(date(due).date() == today(), "Today", ...))'
  # ... 40+ more formulas
views:
  - type: tasknotesTaskList
    name: "All Tasks"
    order: [status, priority, due, scheduled, projects, contexts, file.tags, blockedBy, file.name, recurrence, complete_instances, file.tasks]
    sort: [{column: due, direction: ASC}]
  - type: tasknotesTaskList
    name: "Not Blocked"
    filters:
      and:
        - or:
          - and: [recurrence.isEmpty(), status != "done"]
          - and: [recurrence, '!complete_instances.contains(today().format("yyyy-MM-dd"))']
        - or:
          - blockedBy.isEmpty()
          - 'list(blockedBy).filter(file(value.uid).properties.status != "done").isEmpty()'
  - type: tasknotesTaskList
    name: "Today" / "Overdue" / "This Week" / "Unscheduled"
    # ... with respective date filters
```

### 3d. `TaskNotes/Views/kanban-default.base` — Kanban Board

```yaml
# Same 40+ formulas as tasks-default.base
views:
  - type: tasknotesKanban
    name: "Kanban Board"
    order: [status, priority, due, scheduled, projects, contexts, file.tags, blockedBy, file.name, recurrence, complete_instances, file.tasks]
    groupBy:
      property: status
      direction: ASC
    options:
      columnWidth: 280
      hideEmptyColumns: false
```

### 3e. `TaskNotes/Views/agenda-default.base` — Agenda View

```yaml
# Same 40+ formulas
views:
  - type: tasknotesCalendar
    name: "Agenda"
    order: [status, priority, due, ...]
    options:
      showPropertyBasedEvents: false
    calendarView: "listWeek"
    startDateProperty: file.ctime
    listDayCount: 7
    titleProperty: file.basename
```

### 3f. `TaskNotes/Views/calendar-default.base` — Full Calendar

```yaml
# Same 40+ formulas
views:
  - type: tasknotesCalendar
    name: "Calendar"
    options:
      showScheduled: true
      showDue: true
      showRecurring: true
      showTimeEntries: true
      showTimeblocks: true
      showPropertyBasedEvents: true
      calendarView: "timeGridWeek"
      customDayCount: 3
      firstDay: 0
      slotMinTime: "06:00:00"
      slotMaxTime: "22:00:00"
      slotDuration: "00:30:00"
```

### 3g. `TaskNotes/Views/mini-calendar-default.base` — Mini Calendars (4 tabs)

```yaml
# Same 40+ formulas
views:
  - type: tasknotesMiniCalendar
    name: "Due"
    dateProperty: due
    sort: [{property: due, direction: ASC}]
  - type: tasknotesMiniCalendar
    name: "Scheduled"
    dateProperty: scheduled
  - type: tasknotesMiniCalendar
    name: "Created"
    dateProperty: file.ctime
  - type: tasknotesMiniCalendar
    name: "Modified"
    dateProperty: file.mtime
```

### 3h. `TaskNotes/Views/relationships.base` — Relationship Views (4 tabs)

```yaml
# Same 40+ formulas
# NOTE: No global filter (no `filters:` at top level)
views:
  - type: tasknotesKanban
    name: "Subtasks"
    filters:
      and:
        - file.hasTag("task")
        - note.projects.contains(this.file.asLink())   # <-- uses `this` context
    groupBy: {property: status, direction: ASC}
  - type: tasknotesTaskList
    name: "Projects"
    filters:
      and:
        - list(this.projects).contains(file.asLink())   # reverse direction
  - type: tasknotesTaskList
    name: "Blocked By"
    filters:
      and:
        - file.hasTag("task")
        - list(this.note.blockedBy).map(value.uid).contains(file.asLink())
  - type: tasknotesKanban
    name: "Blocking"
    filters:
      and:
        - file.hasTag("task")
        - list(note.blockedBy).map(value.uid).contains(this.file.asLink())
    groupBy: {property: status, direction: ASC}
```

---

## 4. Duplicate EC_extraCredit Frontmatter Key Issue

### Summary

**10 files** have duplicate YAML frontmatter keys:
- **9 files** with duplicate `EC_extraCredit:` key
- **1 file** with duplicate `EC_expectedDomains:` key

### Affected Files

| File | Duplicate Key |
|------|---------------|
| `SAQ/ANZCA/AP12B/AP12B06.md` | `EC_extraCredit` |
| `SAQ/CICM/CP20A/CP20A-AM/CP20A03.md` | `EC_extraCredit` |
| `SAQ/CICM/CP09B/CP09B-AM/CP09B04.md` | `EC_extraCredit` |
| `SAQ/CICM/CP09B/CP09B-PM/CP09B15.md` | `EC_extraCredit` |
| `SAQ/CICM/CP09A/CP09A-PM/CP09A23.md` | `EC_extraCredit` |
| `SAQ/CICM/CP07B/CP07B-AM/CP07B04.md` | `EC_extraCredit` |
| `SAQ/CICM/CP08B/CP08B-PM/CP08B20.md` | `EC_extraCredit` |
| `SAQ/CICM/CP16A/CP16A-AM/CP16A06.md` | `EC_extraCredit` |
| `SAQ/CICM/CP16A/CP16A-AM/CP16A10.md` | `EC_extraCredit` |
| `SAQ/CICM/CP08B/CP08B-PM/CP08B21.md` | `EC_expectedDomains` |

### Pattern

The duplicates occur when the examiner's report has two separate `EC_extraCredit:` YAML lists. Example from `AP12B06.md`:

```yaml
EC_extraCredit:       # First occurrence (line 48)
- "Many candidates quite rightly mentioned..."
- "Interference with calcium's role..."
- "Good marks were given..."
- "In addition a description of receptor..."
EC_extraCredit:       # Second occurrence (line 53) — DUPLICATE!
- "Moreover, drugs which stabilise mast cell membranes..."
```

### Impact

- **Obsidian itself** handles this gracefully (second value wins silently)
- **obaq CLI** fails completely — strict YAML parsing causes the entire vault parse to abort
- **Fix:** Merge the two lists into one `EC_extraCredit:` key per file

### Additional Stats

- 24 files total mention `EC_extraCredit` (only 9 have duplicates)
- 0 duplicate keys in the LO/ directory
- The `LO/` directory has no duplicate key issues at all

---

## 5. Obsidian Bases Plugin API (from running instance)

### Plugin Instance: `app.internalPlugins.plugins.bases.instance`

```typescript
{
  id: "bases",
  name: "Bases",
  description: "Create custom views that let you edit, sort, and filter files using their properties.",
  
  // Methods
  init()                                    // Initialize plugin
  onEnable()                                // Called when enabled
  createAndOpenBase(event?)                  // Create new .base file and open it
  createAndEmbedBase(editorContext)          // Create .base and embed as ![[file.base]] in editor
  createNewBasesFile(folder, name?, content?) // Create a new .base file (returns TFile)
  registerView(viewId: string, registration) // Register a custom view type
  deregisterView(viewId: string)            // Unregister a view type
  getRegistration(viewId: string)           // Get single view registration
  getRegistrations()                        // Get all registered view types
  getViewFactory(viewId: string)            // Get factory function for a view type
  onFileMenu(menu, file)                    // File context menu handler
  onEditorMenu(menu, editor)                // Editor context menu handler
}
```

### View Registration Format

```typescript
registerView(viewId: string, registration: {
  name: string;       // Display name (e.g., "Table")
  icon: string;       // Lucide icon name (e.g., "lucide-table")
  factory: Function;  // Creates the view component
  options: Function;  // Returns view options/config
})
```

### Built-in View Registrations

| viewId | name | icon |
|--------|------|------|
| `table` | Table | `lucide-table` |
| `cards` | Cards | `lucide-layout-grid` |
| `list` | List | `lucide-list` |

**Note:** The `tasknotesCalendar`, `tasknotesKanban`, `tasknotesMiniCalendar`, `tasknotesTaskList` view types found in the .base files are NOT registered — they come from a community plugin (TaskNotes) that isn't installed in this environment.

### Commands

| Command ID | Name |
|------------|------|
| `bases:new-file` | Bases: Create new base |

### File Type Registration

- Extension `.base` → view type `"bases"`
- Opens in a dedicated `BasesView` (not a text editor)

### BasesView Instance (open .base file)

**Key properties:**
- `view.file` — The TFile for the .base file
- `view.query` — Parsed query object with: `views`, `formulas`, `properties`, `unrecognizedData`, `file`, `saveFn`
- `view.controller` — The query execution controller
- `view.data` — Raw YAML text
- `view.dirty` — Whether unsaved changes exist

**Key methods:**
- `showSearch()`, `load()`, `onLayoutChange()`
- `getViewData()` / `setViewData()` — Get/set raw YAML
- `getState()` / `setState()` / `setEphemeralState()` / `getEphemeralState()`
- `saveQuery()` — Persist query changes
- `clear()` — Clear the view
- `onViewChanged()` — Handle query changes

### BasesController Instance (query execution engine)

**Key properties:**
- `controller.query` — The parsed BaseQuery
- `controller.results` — Map<TFile, ResultRow> (1542 results for SAQ view)
- `controller.errors` — Error collection
- `controller.searchQuery` — Current search text
- `controller.queryState` — Serialized filter AST + formulas (JSON)
- `controller.viewName` — Active view tab name
- `controller.relevantProperties` — Set of property names used
- `controller.currentFile` — Current file context (for `this`)

**Key methods:**
- `runQuery(event)` — Execute the query against vault
- `buildBasesContext(viewFilter)` — Create query context: `new BasesContext(app, combinedFilter, formulas, currentFile)`
- `getProperties()` — Get all available properties (file + note + formula)
- `update()` — Refresh results
- `setQuery(query)` / `setQueryAndView(query, viewName)`
- `selectView(viewName)` — Switch active view tab
- `updateSearchQuery(text)` — Apply text search
- `updateCurrentFile(file)` — Update `this` context
- `addResult(file, row)` / `removeResult(file)`
- `getWidgetForIdent(ident)` — Get UI widget for a property
- `applySearchQuery()` — Filter by search text
- `promptForAddView()` — UI to add new view

### Result Row Structure

Each result in `controller.results` (Map) has:
```typescript
{
  ctx: object;              // Evaluation context
  file: VaultFile;          // The source file
  frontmatter: object;      // Raw frontmatter data
  note: { icon, data };     // Note metadata
  implicit: { icon, app, file, _cachedProps };
  formulaResults: {
    ctx: object;
    formulas: object;
    cachedFormulaOutputs: {   // Computed formula values
      [formulaName]: {
        icon: string;         // e.g., "lucide-text", "lucide-check-square", "lucide-binary"
        data: any;            // The computed value
      }
    }
  }
}
```

### Query State AST (parsed filter)

```json
{
  "filter": {
    "conjunction": "and",
    "filters": [
      {
        "rule": {
          "text": "file.inFolder(\"SAQ\")",
          "formula": {
            "type": "function",
            "name": "inFolder",
            "subject": {"type": "ident", "id": "file"},
            "args": [{"type": "primitive", "value": "SAQ"}]
          }
        }
      }
    ]
  },
  "formulas": { ... }
}
```

---

## 6. Ecosystem

### Community View Plugins (registered via `bases.registerView()`)

| Repo | View Type | Description |
|------|-----------|-------------|
| obsidianmd/obsidian-maps | map | Interactive map view |
| ewerx/obsidian-bases-kanban | kanban | Draggable kanban cards |
| mProjectsCode/obsidian-bases-charts-plugin | charts | Charts and graphs |
| xjiaxiang/obsidian-bases-timeline-view | timeline | Timeline view |
| Quorafind/Obsidian-Bases-Canvas | canvas | Canvas view |
| lhassa8/obsidian-bases-gantt | gantt | Gantt chart |
| seventhxiv/obsidian-board-view | board | Board (kanban/gallery) |
| sean2077/obsidian-bases-paginator | paginated-table | Paginated tables |
| ajgxyz/bases-enhanced-list-view | enhanced-list | Enhanced list |

### Utility Plugins

| Repo | Purpose |
|------|---------|
| davidvkimball/obsidian-bases-cms | CMS-style management |
| astrooom/mysql-to-obsidian-bases | MySQL → .base converter |
| theol0403/obsidian-bases-new-with-template | Template on new entry |
| Signynt/virtual-content | Display bases in notes without modifying |
| tcyeee/obsidian-bases-lock | Lock bases toolbar |
| EzraMarks/obsidian-bases-css-guide | CSS styling guide |
| bennyyip/obsidian-bases-toc | Table of contents |

### Official Documentation

- https://help.obsidian.md/bases
- https://help.obsidian.md/bases/syntax
- https://help.obsidian.md/bases/functions
- https://help.obsidian.md/formulas
