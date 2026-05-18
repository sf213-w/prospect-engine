---
name: repo-docs
description: >
  Generate comprehensive repository documentation from any Git repository. Use this skill
  whenever the user wants to document a codebase, create or improve a README, write plain-language
  or jargon-free explanations of a project, or produce documentation for both technical and
  non-technical audiences. Triggers on phrases like "document this repo", "write a README",
  "explain this codebase", "generate docs", "make documentation for my project", "jargon-less docs",
  "non-technical summary of this code", or any request to document, explain, or describe a
  Git repository or software project. Also use this skill if the user uploads code files,
  pastes a file tree, or shares a GitHub URL and asks for any kind of documentation or explanation.
---
 
# Repo Docs Skill
 
Generate two companion documents for any Git repository:
 
1. **`README.md`** — a comprehensive, professional README for developers and technical readers
2. **`PLAIN_ENGLISH.md`** — a jargon-free explanation for non-technical stakeholders, managers, or the general public
---
 
## Step 0 — Gather Repository Information
 
Accept repo input in any of these forms:
 
| Input type | How to handle |
|---|---|
| **GitHub URL** | Use `web_fetch` to fetch the raw file tree and key files (README, package.json, pyproject.toml, etc.) |
| **Uploaded files / zip** | Read from `/mnt/user-data/uploads/`. Use `view` on directories and `bash_tool` to inspect file contents. |
| **Pasted file tree or code** | Work from what's in the conversation context |
| **Local repo (terminal access)** | Run `find . -type f | head -80` and read key files via `bash_tool` |
 
Before writing anything, collect:
- Project name and purpose (from package.json, pyproject.toml, Cargo.toml, setup.py, go.mod, etc.)
- Tech stack (languages, frameworks, major dependencies)
- Entry points (main file, CLI commands, web server)
- Directory structure (top-level folders and what each does)
- Existing README or docs (if any — preserve accurate content)
- License
- Any tests, CI config, or contribution guidelines
If the user only provides a URL, fetch these paths (substitute the repo root):
```
README.md  •  package.json  •  pyproject.toml  •  Cargo.toml  •  setup.py
go.mod  •  requirements.txt  •  src/  •  lib/  •  main.*  •  index.*
```
 
---
 
## Step 1 — Understand the Project Deeply
 
Before writing, form a clear mental model:
 
- **What problem does this solve?** (one sentence)
- **Who is the intended user?** (developer tool, end-user app, library, API, CLI, etc.)
- **What are the key components?** (services, modules, data models)
- **What does "running it" look like?** (install steps, config, launch command)
- **Are there any notable design decisions or architectural patterns?**
If anything is unclear, ask the user one focused question rather than guessing.
 
---
 
## Step 2 — Write `README.md`
 
Follow the structure in `references/readme-template.md`. Key rules:
 
- **Lead with value** — first paragraph explains what the project does and why it matters
- **Installation must work** — copy-paste commands exactly as they should be run
- **Use real examples** — don't write placeholder `<your_value>` without context
- **Badges** — include only if the repo has CI, npm/PyPI/crates.io, or a license (don't invent them)
- **Keep it scannable** — use headers, code blocks, and short paragraphs
- **Accurate tech stack** — only list what's actually in the repo
Mandatory sections (in order):
1. Project title + one-line description
2. Badges (if applicable)
3. Overview / What is this?
4. Features
5. Tech stack
6. Getting started (prerequisites → installation → configuration → run)
7. Usage (with real code/command examples)
8. Project structure (annotated directory tree)
9. Contributing (if the repo seems open-source)
10. License
---
 
## Step 3 — Write `PLAIN_ENGLISH.md`
 
Read `references/plain-english-guide.md` for detailed tone and structure guidance.
 
Core rules:
- **No jargon without immediate plain explanation** — "API (a way for two programs to talk to each other)"
- **Lead with the human problem** — not the technical solution
- **Use analogies** — compare technical concepts to everyday things
- **Avoid passive voice** — "the app sends your data" not "data is transmitted"
- **Short sentences** — aim for under 20 words per sentence
- **No code blocks** — replace with plain descriptions of what happens
Mandatory sections:
1. What is this? (elevator pitch, 2–3 sentences)
2. What problem does it solve? (the pain point, in human terms)
3. Who is it for?
4. How does it work? (the key idea, no code)
5. What are the main parts? (components explained like rooms in a building)
6. How would I use it? (a realistic day-in-the-life walkthrough)
7. What does it need to run? (system requirements in plain terms)
8. Glossary (define any technical terms that couldn't be avoided)
---
 
## Step 4 — Output
 
Save both files:
- `/mnt/user-data/outputs/README.md`
- `/mnt/user-data/outputs/PLAIN_ENGLISH.md`
Then call `present_files` with both paths.
 
Briefly tell the user:
- What you based the docs on (which files you read)
- Any assumptions you made (e.g. "I assumed this is a public open-source project")
- Anything you couldn't determine and left as a placeholder
---
 
## Quality Checklist
 
Before saving, verify:
- [ ] Installation commands are syntactically correct for the detected package manager
- [ ] Project name matches what's in the config files (not a guess)
- [ ] No placeholder text left (like `[TODO]` or `your-project-name`) unless truly unknown
- [ ] PLAIN_ENGLISH.md contains zero unexplained acronyms
- [ ] Both files are complete — not truncated
- [ ] Code blocks in README use the correct language tag (```bash, ```python, etc.)
 
