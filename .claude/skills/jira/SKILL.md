---
name: jira
description: >-
  Work with the FoodMe Jira project (SCRUM, "AI in QA") through the Atlassian MCP
  connector: file bug reports, search and list issues, read an issue, add
  comments (e.g. verification or test results), move issues between To Do /
  In Progress / Done, and edit summaries, labels or descriptions. Use when the
  user mentions Jira, a SCRUM-NN key, "file/log/report a bug", "create a ticket",
  "close/verify the bug", "what's open", or wants test results posted to an issue.
---

# Jira (FoodMe)

All Jira work goes through the claude.ai Atlassian MCP tools (`mcp__claude_ai_Atlassian_MCP__*`). Load the ones you need with a single `ToolSearch` `select:` call before using them.

## Fixed context
- **cloudId:** `7c653394-26fd-45f8-9c05-331bf0bfa650` (site `julfayanhakob91.atlassian.net`). Don't call `getAccessibleAtlassianResources` unless a call fails with an access or cloudId error.
- **Project:** `SCRUM` ("AI in QA"), a team-managed software project.
- **Workflow statuses:** `To Do` → `In Progress` → `Done`.
- **Issue links:** `https://julfayanhakob91.atlassian.net/browse/<KEY>`
- **Live app (for bug environments):** `https://foodme-hakobjulfayan.onrender.com` (storefront), `/backoffice` (admin).

## Tools
| Goal | Tool |
|---|---|
| Find or list issues | `searchJiraIssuesUsingJql` |
| Read one issue | `getJiraIssue` (`view: "evidence"` gives the description, comments and labels) |
| Read comments | `listJiraIssueComments` |
| Create | `createJiraIssue` |
| Edit fields or description | `editJiraIssue` |
| Comment | `addOrEditJiraIssueComment` |
| Change status | `transitionJiraIssue` (list the transitions first if you don't know the id) |
| Anything else (attachments, links, issue types, sprints) | `discover`, then `executeRead` / `executeWrite` |

**JQL must be bounded.** An unbounded query (e.g. just `order by updated`) returns a 400 error. Always start with `project = SCRUM`. Useful queries:
- Open bugs: `project = SCRUM AND labels = bug AND statusCategory != Done ORDER BY created DESC`
- In progress: `project = SCRUM AND status = "In Progress"`
- Text search: `project = SCRUM AND text ~ "cart"`
- Per seeded bug: `project = SCRUM AND text ~ "FM-BUG-07"`

Pass `fields: ["summary","status","labels","priority","assignee"]` when listing so responses stay small. Show results as a short table with key (linked), summary and status.

## Filing a bug
1. **Check for duplicates first:** search `project = SCRUM AND text ~ "<key words>"`. If a match exists, show it to the user and don't create a new issue.
2. **Reproduce or gather evidence before writing.** A report needs concrete steps and observed values (quantities, prices in AMD, messages). If you haven't seen the behavior yourself, take the facts from the user and don't invent any. Ask for anything that's missing.
3. **Fields:**
   - Issue type: `Task`. SCRUM has no `Bug` issue type (using `issuetype = Bug` in JQL causes an error), so bugs are identified by the `bug` label and the `[Bug]` prefix.
   - Summary: `[Bug] <Area>: <what goes wrong> instead of <what should happen>`
   - Labels: `bug`, `foodme`, plus the area (`cart`, `checkout`, `auth`, `orders`, `admin`, `api`, ...)
   - Priority: `Medium` unless the user says otherwise or it blocks ordering/checkout (then `High`).
4. **Description (markdown).** Follow this template, which matches SCRUM-5:

```markdown
## Environment

* **URL:** <exact page URL>
* **Browser:** <browser, desktop/mobile>
* **User:** <Guest / signed-in role>

## Preconditions

<state before step 1, e.g. "The cart is empty.">

## Steps to reproduce

1. ...
2. ... (bold UI labels: **+**, **Your order**; state the visible result after key steps)

## Actual result

<what happens, as bullet points with observed values>

## Expected result

<what should happen, with concrete expected values>

## Additional notes

* Reproduced N out of N attempts.
* <variants that do or don't reproduce, console/network errors or "no console messages">
```

   Add `## Attachment` only when you actually attach something.
5. **Code references.** If you found the cause in the repo, add a short `## Technical notes` section with `file:line`. If the code has an `// FM-BUG-NN` marker there, include its id. Don't fix the code: seeded bugs stay unless the user asks.
6. Before creating the issue, show the user the summary and description and wait for confirmation (creating it is visible to anyone on the project). Then create it and reply with the key and link.

## Verifying a fix and closing
1. Read the issue, then re-run its steps. Use the `run-tests` / `write-e2e-tests` skills or the browser if appropriate.
2. Post a comment in this format (as on SCRUM-5):

```markdown
Bug is fixed in version **<version or commit>**. Verified and closing.

<one or two sentences: the original steps now give the expected result, with values>

**Regression checks passed:**

* <related scenario>: <result>
* ...

**Tested on:** <browser/env, user>. Not covered: <what you didn't test>.
```

   If it is **not** fixed, comment with what still fails and leave the status as it is (or move it back to `To Do` if the user asks).
3. Transition to `Done` only after a passing verification.

## Rules
- Confirm with the user before every write (create, edit, comment, transition), unless they already asked for that exact action in this turn.
- Report honestly: say what you tested and what you didn't. Never claim a check you didn't run.
- Don't put secrets, tokens or the user's email address in issues.
- Keep the user's language and terms. Write issue text in clear, plain English unless asked otherwise.
