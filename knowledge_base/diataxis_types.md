# Diátaxis Documentation Types

Diátaxis defines four documentation types. Each has a distinct purpose, audience need, and content standard. Mixing types is the most common documentation error. This guide adds a fifth, practical type — overview — for navigational index pages that don't fit any of the four (see below).

## Classify before scoring structure

Before evaluating the Structure criterion, identify which type the
document is functioning as: tutorial, how-to guide, reference, explanation,
or overview (a practical addition beyond strict Diátaxis — see "Overview /
Index Pages" below). Base this on, in order of priority:

1. An explicit `docType` frontmatter field, if present.
2. The document's stated purpose (frontmatter title/description).
3. The content pattern itself (step-by-step instructions vs. field-by-field
specification vs. conceptual reasoning vs. learning-oriented walkthrough).

Apply only the structural requirements for the identified type:

- **Tutorial**: learning-oriented, sequential steps, guaranteed outcome.
- **How-to guide**: task-oriented, numbered steps, prerequisites, an
  outcome/result section.
- **Reference**: complete, self-contained technical specification
  (parameters, schemas, status codes, examples).
- **Explanation**: conceptual reasoning; may link out to reference material
  for procedural or technical detail; does not require numbered steps or
  full parameter tables.
  - **Overview**: navigational index for a section; brief orientation plus
  categorized links. Does not require parameter tables, numbered steps, or
  conceptual depth.

Do not penalize a document against the checklist for a type it is not
attempting to be. If the frontmatter's `docType` disagrees with what the
content pattern suggests, note the mismatch as a separate observation, but
still evaluate structure against the declared `docType`.

## Tutorials

A tutorial is a learning-oriented experience that guides a newcomer through a practical task from start to finish.

**Purpose:** Build competence through doing. The reader learns by following steps, not by reading about concepts.

**Requirements:**

- Concrete, achievable outcome that works the first time
- Prerequisites listed at the top (tools, accounts, dependencies)
- Numbered steps in sequential order
- Every command and code example is complete and runnable
- Tells the reader what they should see at each step
- No decision points — the tutorial makes all choices for the learner
- Ends with a working result the reader can see or verify

**What does not belong:**

- Explanations of why things work
- Options or alternatives mid-tutorial
- Reference tables for parameters
- Links to "read more" mid-step (link at the end instead)

**Common completeness gaps:**

- Missing prerequisite versions (e.g., "Python 3.x" is vague; specify minimum version)
- Steps that assume context not yet established
- No verification step after key actions
- Code examples with placeholder values not clearly marked

## How-to Guides

A how-to guide is a task-oriented document for a reader who already has baseline competence and wants to accomplish a specific goal.

**Purpose:** Help an experienced user complete a real-world task. Unlike tutorials, how-to guides assume prior knowledge.

**Requirements:**

- Clear, specific title that names the task (e.g., "Configure webhook retries")
- Short context line: what this guide does and when to use it
- Prerequisites (tools, permissions, prior setup)
- Numbered steps
- Response or outcome section showing what success looks like
- Links to related reference docs (not inline parameter tables)

**What does not belong:**

- Step-by-step explanation of underlying concepts
- Inline API reference tables (link to reference instead)
- History or background of the feature

**Common completeness gaps:**

- Missing response section — reader doesn't know if it worked
- No error handling guidance for the most common failure
- Prerequisites buried mid-guide instead of listed at top

## Reference Docs

A reference document is information-oriented material that describes the system accurately and completely.

**Purpose:** Give practitioners the facts they need. This is looked up, not read cover to cover.

**Requirements:**

- Every endpoint: HTTP method, path, description
- Every parameter: name, type, required/optional, description, example value
- Every request body field: name, type, required/optional, description, constraints
- Every response field: name, type, description
- HTTP status codes returned and their meaning
- At least one complete, realistic request/response example
- Error codes and their meaning
- Authentication requirements

**What does not belong:**

- Procedural steps or tutorials
- Conceptual explanations of why the API works this way
- Marketing language

**Common completeness gaps:**

- Parameters documented without types
- Required vs. optional not specified
- No example values — descriptions alone are insufficient
- Error codes listed without descriptions
- Authentication method stated but not demonstrated

## Explanation Docs

An explanation document is understanding-oriented material that clarifies concepts, context, or decisions.

**Purpose:** Help the reader understand *why*, not *how*. Explanation docs build mental models.

**Requirements:**

- Answers "why does this work this way?" or "what is this concept?"
- Conceptual diagrams or mental models where helpful
- Links to related tutorials, how-to guides, and reference
- No procedural steps or commands

**What does not belong:**

- Step-by-step instructions
- API reference tables
- Code examples (unless illustrating a concept, not teaching a task)

**Common completeness gaps:**

- Missing links to the how-to or reference doc that applies the concept
- Explanation that drifts into tutorial territory (starts adding steps)

## Overview / Index Pages

*Practical addition — not one of the four canonical Diátaxis types.*

An overview page is a navigational index for a documentation section. It orients the reader and routes them to the tutorials, how-to guides, reference pages, or explanations that actually contain the content. It does not teach, instruct, specify, or explain in its own right.

**Purpose:** Help the reader find the right page quickly. The value is in accurate routing, not depth.

**Requirements:**

- A brief statement of what the section covers
- Categorized links to the section's actual content
- Links that are accurate and point to real, current pages

**What does not belong:**

- Numbered steps or procedures
- Parameter tables, schemas, or error codes
- Extended conceptual reasoning
- Any content that duplicates what a linked page already covers

**Common completeness gaps:**

- Links that are broken, missing, or point to the wrong page
- Sections of the documentation that exist but aren't linked from the overview
- A description vague enough that the reader can't tell which link to follow

Do not score completeness or structure against reference, how-to, or explanation requirements for a page declared as `docType: overview`. Near-total reliance on links is correct for this type, not a gap.
