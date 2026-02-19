# Obsidian Bases / .base File Ecosystem Research

## 1. What is "Bases"?

**Bases is an Obsidian core plugin** (enabled in gkg vault's `core-plugins.json` as `"bases": true`). It provides a database/query view system using `.base` files. It was introduced in Obsidian **v1.10.0** (based on API type annotations).

`.base` files are **YAML-based configuration files** that define:
- **filters** - queries to select which vault files to include
- **formulas** - computed/derived properties (expression language)
- **properties** - display name overrides for note properties
- **summaries** - summary formulas across entries
- **views** - array of view configurations (table, calendar, kanban, etc.)

## 2. npm Package "basemd" - UNRELATED

`basemd@1.0.0` on npm is an **unrelated tool** by `yehan-s`. It's a "Unified AI agent rules manager" that creates symlinks for AGENTS.md, CLAUDE.md, GEMINI.md pointing to a single base.md file. **Nothing to do with Obsidian Bases.**

## 3. Relevant npm Packages

### @type32/obsidian-bases-parser (v0.3.0)
- **A TypeScript parser for .base files** - includes schema definitions, lexer, parser, evaluator, and reactive query system with Vue integration
- Published 2026-02-04
- Dependencies: js-yaml, vue
- 584.5 kB unpacked

### obaq (v1.1.0)  
- **CLI query processor for Obsidian Bases**
- By `knu` (Akinori Musha) - https://github.com/knu/obaq
- Commands: `obaq -e YAML` or `obaq PATH.md`
- Options: `-d VAULT_DIR`, `-e YAML`, `-f FORMAT` (json/csv/md/markdown), `-t PATH` (this file context)
- Dependencies: acorn, gray-matter, js-yaml, remark, etc.
- Published 2026-02-05
- **This is the closest to a CLI tool for querying .base files from the command line**

## 4. Official Obsidian API (obsidian.d.ts)

The Obsidian API defines 78+ Bases-related types. Key types:

### BasesConfigFile (the .base file schema)
```typescript
interface BasesConfigFile {
  filters?: BasesConfigFileFilter;
  properties?: Record<string, Record<string, any>>;  // e.g. displayName overrides
  formulas?: Record<string, string>;                   // computed properties
  summaries?: Record<string, string>;                  // summary formulas
  views?: BasesConfigFileView[];                       // view configurations
}
```

### BasesConfigFileFilter
```typescript
type BasesConfigFileFilter = string | { and: BasesConfigFileFilter[] } | { or: BasesConfigFileFilter[] } | { not: BasesConfigFileFilter[] };
```

### BasesConfigFileView
```typescript
interface BasesConfigFileView {
  type: string;           // view type ID (e.g. "table", "tasknotesCalendar", etc.)
  name: string;           // display name
  filters?: BasesConfigFileFilter;  // per-view additional filters
  groupBy?: { property: string; direction: string };
  order?: string[];       // ordered property IDs to display
  summaries?: Record<string, string>;
  sort?: BasesSortConfig[];  // not in official type but used in practice
}
```

### BasesPropertyId
```typescript
type BasesPropertyId = `${BasesPropertyType}.${string}`;
type BasesPropertyType = 'note' | 'formula' | 'file';
// Examples: "note.status", "formula.daysUntilDue", "file.name", "file.ctime"
```

### Plugin Registration
```typescript
// Plugins register custom view types:
registerBasesView(viewId: string, registration: BasesViewRegistration): boolean;

interface BasesViewRegistration {
  name: string;
  icon: IconName;
  factory: BasesViewFactory;
  options?: (config: BasesViewConfig) => BasesAllOptions[];
}
```

## 5. .base Files Found in gkg Vault

### TaskNotes/Views/ (6 files - all from TaskNotes plugin)
All share the same formula definitions (priorityWeight, daysUntilDue, urgencyScore, timeTracking, etc.) and filter `file.hasTag("task")`.

| File | View Types | Description |
|------|-----------|-------------|
| `agenda-default.base` | `tasknotesCalendar` (listWeek) | 7-day agenda view |
| `calendar-default.base` | `tasknotesCalendar` (timeGridWeek) | Full calendar with scheduled/due/recurring |
| `kanban-default.base` | `tasknotesKanban` | Kanban grouped by status |
| `mini-calendar-default.base` | `tasknotesMiniCalendar` (×4) | Due/Scheduled/Created/Modified mini calendars |
| `relationships.base` | `tasknotesKanban` + `tasknotesTaskList` (×4) | Subtasks, Projects, Blocked By, Blocking views |
| `tasks-default.base` | `tasknotesTaskList` (×6) | All Tasks, Not Blocked, Today, Overdue, This Week, Unscheduled |

### LO/lo.base
- Domain-specific (medical education - Learning Objectives)
- Filters: `file.path.startsWith("LO_linked")` && `file.hasProperty("sectiondomain")`
- Complex formulas for college categorization, verb taxonomy, relationship counting
- Properties section with displayName overrides
- Single table view with 80+ columns

### SAQ/saq.base
- Domain-specific (Short Answer Questions for medical exams)
- Filters: `file.inFolder("SAQ")` && `file.hasProperty("ec.expected")`
- Formulas for pass rates, difficulty tiers, cross-referencing
- Single table view with 60+ columns

## 6. .base File Format Summary (Inferred Spec)

```yaml
# Title (Markdown heading, optional)

# Top-level filters apply to all views
filters:
  and:
    - file.hasTag("task")              # string filter expressions
    - file.path.startsWith("folder/")
    - file.inFolder("folder")
    - file.hasProperty("propName")

# Computed columns available as formula.xxx
formulas:
  formulaName: 'expression using properties, functions, and operators'

# Property display overrides
properties:
  note.propertyName:
    displayName: "Display Name"

# Views array - each is a tab
views:
  - type: table                    # Built-in: table. Plugins: tasknotesCalendar, tasknotesKanban, etc.
    name: "View Name"
    filters:                       # Additional per-view filters
      and: [...]
    order:                         # Column/property display order
      - status
      - formula.daysUntilDue
      - file.name
    sort:
      - property: due              # or column: formula.xxx
        direction: ASC
    groupBy:
      property: status
      direction: ASC
    # View-type-specific options:
    options:
      showScheduled: true
      columnWidth: 280
    # Calendar-specific:
    calendarView: "timeGridWeek"
    startDateProperty: file.ctime
    dateProperty: due
    titleProperty: file.basename
```

### Formula Expression Language
- Conditionals: `if(cond, then, else)`
- Property access: `property`, `file.ctime`, `file.mtime`, `file.name`, `file.basename`, `file.path`
- Date functions: `date()`, `today()`, `now()`, `.format("YYYY-MM")`, `.date()`
- Numeric: `number()`, `.floor()`, `.round()`, `min()`, `max()`
- String: `+` concatenation, `.isEmpty()`, `.contains()`, `.startsWith()`
- List: `list()`, `.length`, `.filter()`, `.map()`, `.reduce()`, `.contains()`
- Comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Boolean: `&&`, `||`, `!`
- Link: `file.asLink()`, `this.file.asLink()`
- Context: `this` refers to the current note (for embedded bases), `value` in lambda contexts

## 7. No Dedicated "basemd" CLI for Obsidian

There is **no official CLI tool from Obsidian** for processing .base files. The ecosystem tools are:
- **obaq** - Third-party CLI that can evaluate .base queries against a vault
- **@type32/obsidian-bases-parser** - TypeScript library for parsing .base files programmatically
