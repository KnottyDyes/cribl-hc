# Cribl Health Check - Screenshot Generation

This directory contains the screenshot generation system for the Cribl Health Check web UI.

## Overview

The screenshot generation system creates realistic UI screenshots (light + dark mode) of the five main pages in the Cribl Health Check web application:

1. **credential_input.png** - Credentials entry page
2. **credential_test_success.png** - Success message after testing credentials
3. **analysis_completion.png** - Analysis summary with health scores
4. **review_analysis_full.png** - Full analysis report with findings table

## Screenshots Generated

All screenshots are generated in both light and dark mode and stored in the `screenshots/` directory:

```
screenshots/
├── light/
│   ├── credential_input.png (1200x800)
│   ├── credential_test_success.png (1200x800)
│   ├── analysis_completion.png (1200x800)
│   ├── review_analysis_full.png (1200x1000)
└── dark/
    ├── credential_input.png (1200x800)
    ├── credential_test_success.png (1200x800)
    ├── analysis_completion.png (1200x800)
    ├── review_analysis_full.png (1200x1000)
```

## How It Works

### Current Implementation: Playwright + Mock Fallback

The current implementation attempts to capture real browser screenshots via Playwright and falls back to mock screenshots if Playwright fails:

- **Location**: `generate_screenshots.py`
- **Approach**: Playwright captures both light/dark with mocked API responses; mock images are used if Playwright fails
- **Advantage**: Real UI when possible, deterministic fallback when not
- **Use Case**: Documentation screenshots for both themes

```bash
/Projects/screenshotter/.venv/bin/python /Projects/screenshotter/generate_screenshots.py
```

### Playwright Requirements

To capture real browser screenshots:

1. **Install Playwright browser**:
   ```bash
   /Projects/screenshotter/.venv/bin/playwright install chromium
   ```

2. **Ensure frontend dev server is running**:
   ```bash
   cd /Projects/cribl-hc/frontend
   npm run dev
   ```

## Component Selector Reference

The script documents all Playwright selectors needed for browser automation. These are extracted from the React component code:

### Credentials Form
```javascript
// Form inputs
input[placeholder="my-cribl-deployment"]      // Name input
input[placeholder="https://cribl.example.com"] // URL input
input[type="password"][...]                     // Token input
select                                          // Auth type selector

// Buttons
button:has-text("Test Credentials")   // Test button
button:has-text("Add Credential")     // Submit button
button:has-text("Cancel")             // Cancel button
```

### Analysis Page
```javascript
button:has-text("Start Analysis")  // Start analysis button
select                              // Deployment selector
.progress                           // Progress indicator
.status-message                     // Status message
```

### Results Page
```javascript
.health-score          // Health score display
.findings-table        // Findings table
.finding-card          // Individual finding cards
.severity-filter       // Severity filter control
```

```javascript
input[placeholder*="company"]  // Company name input
input[type="file"]            // Logo upload input
input[type="color"]           // Color picker inputs
button:has-text("Save Settings") // Save button
```

## Technical Details

### Dependencies

- **PIL (Pillow)**: For generating mock screenshots
- **Playwright** (optional): For real browser automation
  - Install with: `pip install playwright`
  - Then install browser: `npx playwright install chromium`

### Generated Screenshot Features

Each mock screenshot includes:

1. **credential_input.png**
   - Form fields (name, URL, auth type, token)
   - Test and Add buttons
   - Helper text for paste functionality

2. **credential_test_success.png**
   - All form fields from credential_input.png
   - Green success banner with checkmark
   - Confirmation message

3. **analysis_completion.png**
   - Overall health score (circular display)
   - Component scores (Resource, Security, Configuration)
   - Summary statistics with severity breakdown

4. **review_analysis_full.png**
   - Findings table with severity badges
   - Category and title columns
   - Severity filtering indicators
   - Sample findings with different severity levels

   - Company name input field
   - Logo upload area
   - Primary/secondary/accent color pickers
   - Save settings button

## Running the Screenshot Generator

### Quick Start

```bash
cd /Projects/screenshotter
python3 generate_screenshots.py
```

This will:
1. Generate all 5 mock screenshots using PIL
2. Display the component selector reference (for future Playwright use)
3. Output guidance on how to switch to real browser automation

### Output

```
======================================================================
Cribl Health Check - Screenshot Generation
======================================================================
Launching browser for actual screenshot capture...
Navigating to credentials page (light)...
✓ light/credential_input.png
...

✓ All screenshots saved to /Projects/screenshotter/screenshots

======================================================================
SELECTOR REFERENCE (For Playwright Automation)
======================================================================
[... selector mappings ...]
```

## Integration with CriblVision Pack

These screenshots are used for:

1. **Documentation** - Visual guides for users
2. **Package README** - Screenshots in the Cribl Exchange documentation
3. **Marketing** - UI mockups for feature announcements
4. **Testing** - Visual regression testing (when using real Playwright automation)

## Code Structure

### `generate_screenshots.py`

**Part 1: Component Selector Mappings**
- Centralized SELECTORS dictionary
- Maps UI components to CSS selectors
- Based on React component code inspection

**Part 2: Mock Screenshot Generation**
- Helper functions for drawing UI elements
- Five screenshot generator functions
- PIL-based rendering

**Part 3: Playwright Automation** (Future)
- Async screenshot capture from real browser
- Proper wait strategies
- Full-page screenshot support

## Development Notes

### Why Keep Mock Screenshots?

1. **Fallback safety**: If Playwright fails, screenshots still generate
2. **Deterministic output**: Same code always produces identical images
3. **Fast**: Generation takes < 5 seconds
4. **Version control friendly**: Small PNG files, no bloat
5. **Offline use**: No need to run servers or services

### Playwright + Mock Flow

The script always attempts Playwright first, then falls back to mocks:

```python
try:
    screenshot_dir = asyncio.run(async_capture_screenshots())
except Exception:
    for theme_label in ["light", "dark"]:
        generate_mock_screenshots(theme_label)
```

## Troubleshooting

### Playwright Installation Issues

If you encounter:
```
Error: Installation process exited with code: 1
```

Try installing system dependencies first:
```bash
# For Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y libnss3 libxss1 libasound2

# Then try Playwright install again
npx playwright install chromium
```

### Font Not Found

The script falls back to default fonts if the system font is unavailable. This is intentional and doesn't affect functionality.

## File Structure

```
/Projects/screenshotter/
├── generate_screenshots.py          # Main script (mock + Playwright code)
├── README.md                        # This file
├── .venv/                           # Virtual environment
└── screenshots/                     # Generated screenshots
    ├── credential_input.png
    ├── credential_test_success.png
    ├── analysis_completion.png
    ├── review_analysis_full.png
```

## Next Steps

1. ✅ Generate light/dark screenshots (DONE)
2. ⏳ Integrate screenshots into CriblVision Pack documentation
3. ⏳ Set up automated screenshot updates in CI/CD pipeline

## Related Documentation

- **CriblVision Pack Documentation**: See `/Projects/cribl-hc/CRIBLVISION_SEARCH_SUMMARY.md`
- **Frontend Code**: `/Projects/cribl-hc/frontend/src/components/`
- **Component Selectors**: See SELECTORS in `generate_screenshots.py`

---

**Last Updated**: 2026-01-11
**Status**: ✅ Complete - All 5 screenshots generated