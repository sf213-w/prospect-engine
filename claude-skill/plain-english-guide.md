# Plain English Documentation Guide

This guide governs how to write `PLAIN_ENGLISH.md` — a jargon-free companion document
for non-technical readers: managers, executives, clients, investors, or curious members of
the public who want to understand what a software project does without needing to read code.

---

## Guiding Philosophy

The goal is not to "dumb things down" — it's to make things genuinely understandable.
Treat the reader as intelligent but unfamiliar with software concepts.

Ask yourself: "Could my grandmother understand this? Could a project manager who has never
written code use this to explain the project in a meeting?"

---

## Voice & Tone

| Do | Don't |
|---|---|
| Write in second person: "you" | Write in passive voice: "data is processed" |
| Use present tense: "the app sends" | Use future-tense hedging: "the system will attempt to" |
| Be concrete: "stores your login details" | Be vague: "manages authentication state" |
| Use short sentences (under 20 words) | Chain clauses with commas and semicolons |
| Use analogies from everyday life | Use technical analogies ("like a hash map") |
| Name the human benefit | Name the technical mechanism |

---

## Jargon Rules

**Rule 1: No unexplained acronym, ever.**
If you must use an acronym, define it immediately in parentheses on first use:
> "The app uses an API (a standard way for two programs to share information) to..."

**Rule 2: Replace jargon with plain equivalents where possible.**

| Jargon | Plain alternative |
|---|---|
| repository / repo | project folder / codebase |
| deploy / deployment | publish / make live / release |
| authenticate / auth | log in / verify your identity |
| database | organized storage / filing system |
| API | a way for programs to talk to each other |
| framework | a set of pre-built tools the developers used |
| dependencies | other software this project relies on |
| server | a computer that runs the software and responds to requests |
| frontend | the part you see and click on |
| backend | the behind-the-scenes part that processes data |
| microservices | separate mini-programs that each handle one job |
| CI/CD | an automated system that tests and publishes the code |
| container / Docker | a self-contained package that makes the software run consistently anywhere |
| library | a collection of pre-written code that solves common problems |
| open source | the code is publicly available and anyone can contribute |
| branch | a separate copy of the code used to work on a new feature |
| merge | combining two versions of the code |
| environment variable | a setting stored outside the code, like a configuration file |
| runtime | while the program is actively running |
| asynchronous | tasks that happen in the background without making you wait |
| latency | delay / how long something takes |
| throughput | how much work the system can do at once |
| cache / caching | saving a copy so it loads faster next time |
| encrypt / encryption | scramble so only authorized people can read it |

**Rule 3: If a technical term has no clean plain equivalent, use it with a brief analogy.**
> "The system uses a cache — think of it like a sticky note with the answer to a question
> you asked recently, so you don't have to look it up again."

---

## Full Template

```markdown
# [Project Name] — Plain English Guide

*A jargon-free explanation for non-technical readers.*

---

## What Is This?

[2–3 sentences. What does this project do at the highest level? Pretend you're explaining
it to someone at a dinner party who just asked "so what does your team work on?"]

Example: "This is a web application that helps small restaurants manage their takeout orders.
Instead of juggling phone calls, paper tickets, and separate apps, restaurant staff can see
every order in one place, in real time."

---

## What Problem Does It Solve?

[Describe the pain point or inefficiency this addresses. Make it feel real and human.
Don't start with the solution — start with the problem.]

Example: "Before this tool existed, the team had to manually download sales reports from
three different systems, copy the numbers into a spreadsheet, and spend hours every Monday
making sure they added up correctly. Mistakes were common, and the process took a full day."

---

## Who Is It For?

[Be specific. List the types of people who would use this and what they'd use it for.]

- **[Role]** — [what they do with it]
- **[Role]** — [what they do with it]

Example:
- **Restaurant managers** — view all incoming orders and mark them as ready
- **Kitchen staff** — see order details on a screen without reading handwritten tickets
- **Owner/operators** — review daily sales summaries and popular items

---

## How Does It Work?

[Explain the core idea without any code. Use an analogy if helpful. Focus on the flow of
information or the main action the software takes.]

Example: "Think of it like a digital bulletin board. When a customer places an order online,
it immediately appears on the restaurant's screen — sorted by time and colour-coded by status.
Staff can tap an order to mark it as in progress or ready, and the customer's tracking page
updates automatically."

---

## What Are the Main Parts?

[Break the project into its major components, explained like rooms in a building or
departments in a company. Avoid technical names where possible.]

| Part | What it does |
|---|---|
| **The dashboard** | The screen restaurant staff look at — shows all live orders |
| **The order intake system** | Receives orders from the customer-facing website |
| **The notification system** | Sends a text message to customers when their order is ready |
| **The reports section** | Shows the owner daily, weekly, and monthly sales summaries |

---

## How Would Someone Use It?

[Walk through a realistic scenario step by step. Use a named character if it helps.
Show the experience from the user's perspective, not the system's perspective.]

Example:
"Imagine it's a Friday evening at Rosie's Pizza. A customer visits the website and orders
a large pepperoni pizza for collection.

1. The order appears instantly on the kitchen screen, showing the customer's name and items.
2. A staff member taps **'Start preparing'** to let the system know it's being made.
3. When the pizza is boxed up, they tap **'Ready for collection'**.
4. The customer automatically receives a text message: 'Your order is ready!'
5. At the end of the night, Rosie checks the summary page to see the day's total revenue
   and which items sold best."

---

## What Does It Need to Run?

[List requirements in plain terms. No version numbers unless essential — explain what
things are if they're not obvious.]

- A computer or server with an internet connection
- [If web app]: A modern web browser (Chrome, Firefox, Safari, Edge)
- [If mobile]: An iPhone or Android phone running a recent version of its operating system
- [If self-hosted]: A hosting service (like a rented server) to run the software on

---

## Glossary

[Define any technical terms that appeared in the document and couldn't be fully avoided.
Alphabetical order.]

| Term | Plain meaning |
|---|---|
| **API** | A standard way for two programs to share information with each other |
| **Database** | An organized digital storage system — like a very large, structured spreadsheet |
| **Open source** | The code is publicly available; anyone can read, use, or contribute to it |
| **Server** | A computer (often rented, often remote) that runs the software and responds to requests |

```

---

## Common Mistakes to Avoid

1. **Explaining how instead of what** — readers want to know what the software does, not how it does it internally. "It uses PostgreSQL" is useless; "it stores all your data in a secure database" is useful.

2. **Too much structure** — don't turn the plain-English doc into a bullet-point wall. Use prose where possible. The goal is readable, not scannable.

3. **Assuming the reader knows the domain** — even industry-specific business terms (like "SKU", "PO", "yield") should be briefly explained if used.

4. **Vague benefit statements** — "improves efficiency" is meaningless. "Cuts the Monday reporting process from 6 hours to 20 minutes" is meaningful.

5. **Forgetting the glossary** — even a well-written doc will sneak in one or two technical terms. Catch them all in the glossary.