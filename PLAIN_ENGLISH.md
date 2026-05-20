# Prospect Engine — Plain English Guide

## What Is This?

Prospect Engine is a tool that automatically finds contact information for healthcare privacy officers. It reads a public government list of hospitals and clinics that have had data breaches, then searches the internet to find the right person to contact at each organization.

---

## What Problem Does It Solve?

When a healthcare organization has a data breach, the U.S. government publishes their name on a public list (sometimes called the "Wall of Shame"). Researchers, compliance professionals, and vendors often need to reach out to these organizations — specifically to their Privacy Officer, the person legally responsible for protecting patient data.

Finding that contact information manually is slow and tedious. You would have to look up each organization one by one, dig through their website, and hope the right email address is listed somewhere. Prospect Engine does all of that automatically, for hundreds of organizations at a time.

---

## Who Is It For?

- **Compliance and legal teams** who need to contact healthcare organizations about data protection matters
- **Researchers** studying healthcare data breach trends and organizational responses
- **Healthcare IT vendors** who want to reach the right decision-maker at organizations with known security needs
- **Developers** who need a starting point for building healthcare outreach tools

---

## How Does It Work?

The tool works in three steps, one after the other:

**Step 1 — Read the Government List**
It opens the HHS (U.S. Department of Health and Human Services) breach report website — the same page anyone can visit at hhs.gov — and reads through the list of healthcare providers who have reported breaches. It collects up to 100 names by default.

**Step 2 — Find Each Organization's Website**
For each organization on the list, it searches the internet (using DuckDuckGo, a search engine) to find the organization's official website. It's smart enough to skip over irrelevant results like Yelp reviews or LinkedIn pages.

**Step 3 — Find the Privacy Officer's Contact Details**
It then visits that organization's website and looks in the most likely places — pages with names like "Privacy Policy," "HIPAA Notice," or "Contact Us." It scans those pages for email addresses and phone numbers that appear near words like "Privacy Officer" or "Compliance Officer." If it can't find anything on the website itself, it does one more internet search specifically targeting the privacy contact.

All results are saved to a spreadsheet file as it goes, so even if something goes wrong partway through, you don't lose the work already done.

---

## What Are the Main Parts?

Think of the project like a small office with several departments:

- **Pipeline** — The engine room. This is where the main scraper lives. It runs the three steps described above.
- **Breach Dashboard** — A visual display that shows breach data in charts and summaries, making it easier to understand at a glance.
- **Splitting Contacts** — A utility that helps divide up a large list of contacts into smaller batches — useful when handing results off to different people or systems.
- **NeverBounce Data** — A folder for email validation results. NeverBounce is a service (like a spell-checker, but for email addresses) that verifies whether an email address actually works before you try to send to it.
- **Data** — Raw and in-progress data files used during processing.
- **PRD & Notes** — Planning documents and development notes that describe what the tool is meant to do and how it evolved.

---

## How Would I Use It?

Here's a realistic walkthrough:

1. You install the tool on your computer (a one-time setup that takes about 5 minutes).
2. You run a single command in your terminal (a text-based window on your computer).
3. The tool opens a hidden web browser and starts working automatically. You don't need to interact with it.
4. After 1–3 hours (depending on how many organizations you're looking up), it creates a spreadsheet on your computer.
5. You open that spreadsheet. Each row is one healthcare organization, with columns for their website, email addresses, phone numbers, and where the information was found.
6. You use that spreadsheet for outreach, research, or import it into another system.

---

## What Does It Need to Run?

- A computer running Windows, Mac, or Linux
- Python 3.8 or newer installed (Python is a free programming language — think of it like the engine the tool runs on)
- An internet connection
- About 5 minutes to install the required components the first time

You do not need any paid accounts or API keys (special access codes for paid services) to run the basic version.

---

## How Long Does It Take?

Each organization takes roughly 30 to 90 seconds to process, because the tool is deliberately slow and polite — it doesn't hammer websites or search engines with rapid-fire requests. A full run of 100 organizations typically finishes in 1 to 3 hours.

---

## Things to Know Before You Use It

- **Results aren't perfect.** The tool does its best, but sometimes it finds the wrong website for an organization, or picks up an email address that belongs to a vendor rather than the organization itself. Always double-check before using contact details for outreach.
- **Some organizations won't have results.** If a privacy contact isn't publicly listed anywhere the tool can find, the organization still appears in the spreadsheet — it's just marked as "not found."
- **Respect website rules.** Websites have terms of service (rules about how they can be used). Use this tool responsibly and in accordance with the law.

---

## Glossary

| Term | Plain English meaning |
|---|---|
| **HIPAA** | A U.S. law (the Health Insurance Portability and Accountability Act) that sets rules for how healthcare organizations must protect patient information |
| **Privacy Officer** | The person at a healthcare organization who is legally responsible for data privacy and HIPAA compliance |
| **HHS OCR** | The U.S. government office (Office for Civil Rights, part of Health and Human Services) that publishes the breach report and enforces HIPAA |
| **Breach Portal / Wall of Shame** | The public government website listing healthcare organizations that have had data breaches affecting 500+ people |
| **Headless browser** | A web browser that runs in the background without showing a window on your screen — the tool uses one to read web pages automatically |
| **CSV / Spreadsheet** | A file format that can be opened in Excel or Google Sheets, organized into rows and columns |
| **DuckDuckGo** | A privacy-focused internet search engine the tool uses to find websites and contact information |
| **Pipeline** | A series of automated steps that run one after another, like an assembly line |
| **API key** | A special password used to access a paid or restricted online service |
| **NeverBounce** | A service that checks whether an email address is real and working before you send to it |
