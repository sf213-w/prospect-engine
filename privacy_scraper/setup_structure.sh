#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Creating privacy_scraper project structure..."

# 1. Create root directory and navigate into it
mkdir -p privacy_scraper
cd privacy_scraper

# 2. Create root level files
touch main.py config.py constants.py schemas.py logging_config.py

# 3. Create subdirectories and their respective files
# hhs
mkdir -p hhs
touch hhs/download_hhs.py hhs/parse_hhs.py hhs/provider_filter.py

# search
mkdir -p search
touch search/ddg_search.py search/website_finder.py search/search_cache.py

# crawl
mkdir -p crawl
touch crawl/fetch_page.py crawl/privacy_paths.py crawl/link_discovery.py crawl/crawl_site.py

# extraction
mkdir -p extraction
touch extraction/extract_emails.py extraction/extract_phones.py extraction/extract_names.py extraction/extract_contacts.py extraction/classify_contact.py

# normalization
mkdir -p normalization
touch normalization/normalize_email.py normalization/normalize_domain.py normalization/normalize_provider.py normalization/normalize_phone.py

# validation
mkdir -p validation
touch validation/domain_validation.py validation/email_validation.py validation/provider_matching.py

# scoring
mkdir -p scoring
touch scoring/contact_score.py scoring/confidence_score.py

# dedupe
mkdir -p dedupe
touch dedupe/dedupe_emails.py dedupe/dedupe_providers.py dedupe/merge_contacts.py

# export
mkdir -p export
touch export/write_csv.py export/excel_report.py export/readme_sheet.py

# utils
mkdir -p utils
touch utils/dates.py utils/retry.py utils/text.py utils/urls.py

# 4. Create remaining empty directories
mkdir -p cache
mkdir -p tests

echo "Project structure successfully created!"