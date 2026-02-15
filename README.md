# AI SEO Content Agent

Fully autonomous multi-agent system for SEO affiliate content generation.

## Features

- Live SERP research using Claude's web_search (no external SERP APIs)
- Competitor analysis using Claude's web_fetch
- 4,000+ word FTC-compliant articles
- Auto-inject Amazon affiliate links
- JSON-LD schema generation (ItemList + Article + FAQPage)
- Auto-publish to WordPress with Rank Math SEO fields
- Batch processing from CSV (1,000+ keywords)
- Quality control with validation checks

## Cost

~$0.02 per article (only Claude API usage - no external APIs needed)

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure `config/config.json`:
   - Add your Anthropic API key
   - Add WordPress credentials (URL, username, application password)
   - Set your Amazon affiliate tag

3. Add keywords to `data/keywords.csv`

4. Populate `config/product_database.json` with products for each category

## Usage

**Single keyword:**

```bash
python main.py --keyword "best laptops 2026" --category laptop --year 2026
```

**Batch mode (all keywords from CSV):**

```bash
python main.py --batch data/keywords.csv
```

**Auto-publish to WordPress:**

```bash
python main.py --batch data/keywords.csv --publish
```

## WordPress Setup

1. Go to WordPress Admin > Users > Your Profile
2. Scroll to "Application Passwords"
3. Create a new application password
4. Copy the credentials into `config/config.json`

## Architecture

```
agents/
  research_agent.py   - SERP research via Claude's web_search + web_fetch
  content_agent.py    - 4,000+ word article generation
  quality_agent.py    - Validation (word count, FTC compliance, schema, links)
  publisher_agent.py  - WordPress REST API publishing with Rank Math SEO
```

## Output

- Articles saved to `data/output/`
- Published URLs tracked in `data/published.json`
- SERP research cached in `data/cache/` (7-day TTL)
