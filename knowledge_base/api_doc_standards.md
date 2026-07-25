# API Documentation Standards

These standards define what complete, accurate, and usable API documentation looks like for REST APIs targeting developer audiences.

## Endpoint Reference Standards

Every REST API endpoint requires the following elements. Missing any of these is a completeness gap.

### Required fields per endpoint

- **HTTP method**: GET, POST, PUT, PATCH, DELETE — stated explicitly
- **Path**: Full path including path parameters in consistent notation (e.g., `/books/{bookId}`)
- **Description**: One to two sentences describing what the endpoint does and when to use it
- **Authentication**: Whether the endpoint requires authentication and what type (Bearer token, API key, OAuth scope)
- **Request parameters**: All path, query, and header parameters documented (see parameter standards below)
- **Request body**: Schema for POST/PUT/PATCH endpoints (see request body standards below)
- **Response**: Success response schema with field descriptions (see response standards below)
- **Error responses**: HTTP status codes the endpoint can return with descriptions
- **Example**: At least one complete, realistic request/response pair

### Parameter standards

Each parameter must include:

- Name (exact string, in code formatting)
- Location: path, query, or header
- Type: string, integer, boolean, array, object
- Required or optional
- Description: what it controls and any constraints (min/max, allowed values, format)
- Example value

Avoid: Documenting only the name and type without explaining constraints or when to use the parameter.

### Request body standards

- Document every field in the request body schema
- Specify required vs. optional for each field
- Specify type and format (e.g., `string (ISO 8601)`, `integer`, `boolean`)
- Describe valid values or ranges for constrained fields
- Show a complete, realistic example request body — not a template with `"string"` placeholders

### Response standards

- Document every field in the success response body
- Specify types and formats
- Describe what each field means, not just its name
- Show a complete, realistic example response
- Document all HTTP status codes returned (not just 200)

### Error code standards

- List every HTTP status code the endpoint returns
- For each: the code, the condition that triggers it, and how to resolve it
- Include example error response bodies where applicable
- 4xx errors should explain what the client did wrong
- 5xx errors should tell the developer what to do (retry, contact support, etc.)

## Deferred completeness for non-reference documents

Explanation, overview, and conceptual documents are not required to inline
every parameter, schema field, or error code they mention. When a document
contains an explicit, named link to a dedicated reference page for that
detail (e.g., "See [Get all books] for the full parameter reference"), do
not score completeness as failing solely because the detail isn't repeated
in this document.

Instead, note the deferral without penalizing the score:
"Defers to [linked page] for parameter details — verify that page actually
contains this information."

Only score completeness as failing when either:
(a) the document references missing information without naming or linking
a specific source ("see the docs" with no link), or
(b) no reference to the missing information exists anywhere in the document.

## Code Example Standards

### Accuracy requirements

- All code examples must be syntactically correct in their language
- Examples must use realistic values, not placeholder strings like `"string"` or `12345`
- Request examples must match the documented schema exactly — no extra or missing fields
- Response examples must match what the API actually returns
- Authentication headers must be shown correctly (e.g., `Authorization: Bearer {token}`, not `Authorization: token`)

### Language conventions

Respect naming conventions per language. These are not inconsistencies:

- JSON field names use camelCase (`bookId`, `createdAt`)
- Python variables use snake_case (`book_id`, `created_at`)
- JavaScript/TypeScript variables use camelCase (`bookId`, `createdAt`)
- Shell/curl examples use hyphenated flag names (`--header`, `--data`)

Flag as inconsistent: mixed conventions within the same language or context, or mismatched field names passed between layers (e.g., a Python script serializing `book_id` as a JSON key when the API expects `bookId`).

### Completeness of examples

A complete code example includes:

- The full request (not just the payload)
- Authentication header
- Content-Type header where required
- The expected response
- Error handling for at least one common failure

## Clarity Standards

### Language

- Use second person ("you") for instructions
- Use active voice
- Use imperative mood for steps ("Set the `limit` parameter", not "The limit parameter should be set")
- Define technical terms on first use
- Avoid jargon that a developer new to this API wouldn't know

### Formatting

- Use code formatting for: endpoint paths, parameter names, field names, values, HTTP methods, status codes
- Use headers to separate logical sections
- Use tables for parameter lists with three or more parameters
- Use numbered lists for sequential steps; use bullet lists for non-sequential items

### Ambiguity signals

Flag clarity issues when:

- A field description restates the field name without adding meaning (e.g., `bookId: The book ID`)
- "Optional" parameters don't describe what happens when omitted
- Conditional behavior is described without specifying the condition
- "See below" or "see above" references that are vague

## Consistency Standards

### Terminology

- Use the same term for the same concept throughout a doc and across docs
- Do not alternate between synonyms (e.g., "webhook" and "callback" for the same feature)
- Match terminology used in the API itself (field names, endpoint names)

### Formatting consistency

- Heading levels consistent with the surrounding documentation
- Code block language identifiers present and consistent (` ```json `, ` ```python `)
- Parameter tables use the same column structure throughout
- Example responses formatted the same way (indented JSON, not inline)

## Integration Guide Standards

Integration guides are how-to docs that walk a developer through implementing a specific feature or use case.

### Required elements

- **Overview**: What the integration does and when to use it
- **Prerequisites**: SDKs, API keys, account configuration required before starting
- **Implementation steps**: Numbered, in order, each focused on one action
- **Code examples**: For each major step, in the developer's expected language
- **Testing**: How to verify the integration is working (sandbox environment, test payloads)
- **Error handling**: Most common integration errors and how to resolve them
- **Next steps**: Links to related reference docs, advanced configurations, or related guides

### Common integration guide gaps

- No sandbox or test mode guidance
- Code examples cover the happy path only — no error handling shown
- Steps assume configuration that hasn't been described
- No explanation of what the developer should see after each step
