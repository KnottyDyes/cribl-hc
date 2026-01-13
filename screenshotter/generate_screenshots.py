"""
Screenshot Generation Script for Cribl Health Check Web UI

This script generates realistic mock screenshots of the web UI by:
1. Creating mock images using PIL that simulate UI screens
2. Using actual component selectors from the codebase
3. Documenting the proper Playwright selectors for actual browser automation

The generated screenshots show:
1. credential_input.png - Credentials entry page
2. credential_test_success.png - Success message after testing connection
3. analysis_completion.png - Analysis summary screen
4. review_analysis_full.png - Full report with findings
5. branding_manager.png - Branding/settings page

To use real Playwright automation instead of mock screenshots:
1. Install Playwright browser: npx playwright install chromium
2. Update the call to use async_capture_screenshots() instead of generate_mock_screenshots()
3. Ensure localhost:5173 is running with: npm run dev (from frontend directory)
"""

import asyncio
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json


# ============================================================================
# PART 1: Component Selector Mappings (Based on Code Inspection)
# ============================================================================

SELECTORS = {
    # Credentials Page Components
    "credential_form": {
        "name_input": 'input[placeholder="my-cribl-deployment"]',
        "url_input": 'input[placeholder="https://cribl.example.com"]',
        "auth_type_select": "select",  # Generic select for auth type
        "token_input": 'input[type="password"][placeholder="Enter your bearer token"]',
        "test_button": 'button:has-text("Test Credentials")',
        "add_button": 'button:has-text("Add Credential")',
        "cancel_button": 'button:has-text("Cancel")',
    },
    # Analysis Page
    "analysis_page": {
        "start_button": 'button:has-text("Start Analysis")',
        "deployment_select": "select",
        "progress_indicator": ".progress",
        "status_message": ".status-message",
    },
    # Results Page
    "results_page": {
        "health_score_display": ".health-score",
        "findings_table": ".findings-table",
        "finding_cards": ".finding-card",
        "severity_filter": ".severity-filter",
    },
    # Branding Page
    "branding_page": {
        "company_name_input": 'input[placeholder*="company"]',
        "logo_upload": 'input[type="file"]',
        "color_picker": 'input[type="color"]',
        "save_button": 'button:has-text("Save Settings")',
    },
}


# ============================================================================
# PART 2: Mock Screenshot Generation
# ============================================================================


def create_text_centered(
    image: Image.Image, text: str, xy: tuple, font_size: int = 20, color: str = "black"
):
    """Helper to draw centered text on an image."""
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except (OSError, IOError):
        # Fallback to default font if specific font not found
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x, y = xy
    draw.text((x - text_width // 2, y - text_height // 2), text, fill=color, font=font)


def draw_input_field(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int = 300,
    height: int = 40,
    label: str = "",
    placeholder: str = "",
):
    """Draw a mock input field."""
    # Draw border
    draw.rectangle([x, y, x + width, y + height], outline="gray", width=1)
    # Draw label if provided
    if label:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        except (OSError, IOError):
            font = ImageFont.load_default()
        draw.text((x, y - 20), label, fill="black", font=font)
    # Draw placeholder text if provided
    if placeholder:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except (OSError, IOError):
            font = ImageFont.load_default()
        draw.text((x + 10, y + 10), placeholder, fill="lightgray", font=font)


def draw_button(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int = 100,
    height: int = 40,
    text: str = "Button",
    bg_color: str = "blue",
):
    """Draw a mock button."""
    draw.rectangle([x, y, x + width, y + height], fill=bg_color, outline="darkgray", width=1)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    except (OSError, IOError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw.text(
        (x + (width - text_width) // 2, y + (height - text_height) // 2),
        text,
        fill="white",
        font=font,
    )


def screenshot_1_credential_input() -> Image.Image:
    """
    Screenshot 1: Credentials entry page
    Shows: form with URL input, token input, auth type selector, test button
    """
    img = Image.new("RGB", (1200, 800), color="white")
    draw = ImageDraw.Draw(img)

    # Header
    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except (OSError, IOError):
        header_font = ImageFont.load_default()

    draw.text((50, 30), "Add Cribl Deployment", fill="black", font=header_font)

    # Draw form fields
    y_pos = 120
    draw_input_field(draw, 50, y_pos, 500, 40, "Credential Name", "my-cribl-deployment")

    y_pos += 80
    draw_input_field(draw, 50, y_pos, 500, 40, "Cribl URL", "https://cribl.example.com")

    y_pos += 80
    draw.rectangle([50, y_pos, 250, y_pos + 40], outline="gray", width=1)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except (OSError, IOError):
        font = ImageFont.load_default()
    draw.text((55, y_pos + 12), "Authentication Type: Bearer Token ▼", fill="black", font=font)
    draw.text((50, y_pos - 20), "Authentication Type", fill="black", font=font)

    y_pos += 80
    draw_input_field(draw, 50, y_pos, 500, 40, "Bearer Token", "●●●●●●●●●●●●")

    # Buttons
    y_pos += 80
    draw_button(draw, 350, y_pos, 120, 40, "Test", "lightblue")
    draw_button(draw, 480, y_pos, 120, 40, "Add Credential", "green")

    # Helper text
    try:
        helper_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except (OSError, IOError):
        helper_font = ImageFont.load_default()
    draw.text(
        (50, 480),
        "💡 Paste a curl command or API URL - we'll extract the base URL and token",
        fill="gray",
        font=helper_font,
    )

    return img


def screenshot_2_credential_test_success() -> Image.Image:
    """
    Screenshot 2: Success message after testing connection
    Shows: Credentials form + green success banner
    """
    img = screenshot_1_credential_input()  # Reuse the form
    draw = ImageDraw.Draw(img)

    # Draw success banner
    draw.rectangle([50, 550, 1100, 650], fill="#d4edda", outline="#28a745", width=2)
    try:
        success_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
        )
    except (OSError, IOError):
        success_font = ImageFont.load_default()
    draw.text((70, 575), "✓ Connection successful!", fill="#155724", font=success_font)
    draw.text(
        (70, 605),
        "The credentials are valid and the Cribl deployment is reachable.",
        fill="#155724",
        font=success_font,
    )

    return img


def screenshot_3_analysis_completion() -> Image.Image:
    """
    Screenshot 3: Analysis summary screen
    Shows: Health score, component scores, summary statistics
    """
    img = Image.new("RGB", (1200, 800), color="white")
    draw = ImageDraw.Draw(img)

    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        score_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        component_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except (OSError, IOError):
        header_font = ImageFont.load_default()
        score_font = ImageFont.load_default()
        component_font = ImageFont.load_default()

    # Title
    draw.text((50, 30), "Analysis Complete", fill="black", font=header_font)

    # Health score circle
    draw.ellipse([100, 150, 300, 350], fill="#4CAF50", outline="darkgreen", width=3)
    draw.text((150, 220), "78", fill="white", font=score_font)
    try:
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except (OSError, IOError):
        label_font = ImageFont.load_default()
    draw.text((110, 360), "Overall Health Score", fill="black", font=label_font)

    # Component scores
    x_offset = 450
    components = [
        ("Resource", 65, "#FF9800"),
        ("Security", 80, "#2196F3"),
        ("Configuration", 90, "#8BC34A"),
    ]

    for i, (name, score, color) in enumerate(components):
        y = 150 + (i * 120)
        draw.rectangle(
            [x_offset, y, x_offset + 300, y + 80], fill=color, outline="darkgray", width=2
        )
        draw.text((x_offset + 20, y + 10), name, fill="white", font=component_font)
        try:
            large_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32
            )
        except (OSError, IOError):
            large_font = ImageFont.load_default()
        draw.text((x_offset + 200, y + 20), str(score), fill="white", font=large_font)

    # Summary statistics
    draw.text((50, 550), "Findings Summary:", fill="black", font=header_font)
    try:
        stat_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except (OSError, IOError):
        stat_font = ImageFont.load_default()

    draw.text((50, 620), "• 1 Critical finding", fill="#d32f2f", font=stat_font)
    draw.text((50, 650), "• 1 High finding", fill="#ff6f00", font=stat_font)
    draw.text((50, 680), "• 1 Medium finding", fill="#fbc02d", font=stat_font)

    return img


def screenshot_4_review_analysis_full() -> Image.Image:
    """
    Screenshot 4: Full report page with findings
    Shows: Findings table with severity colors, detailed finding cards
    """
    img = Image.new("RGB", (1200, 1000), color="white")
    draw = ImageDraw.Draw(img)

    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        table_header_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12
        )
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except (OSError, IOError):
        header_font = ImageFont.load_default()
        table_header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title
    draw.text((50, 30), "Analysis Report", fill="black", font=header_font)

    # Table header
    y = 100
    draw.rectangle([50, y, 1100, y + 40], fill="#f5f5f5", outline="gray", width=1)
    draw.text((60, y + 10), "Severity", fill="black", font=table_header_font)
    draw.text((150, y + 10), "Category", fill="black", font=table_header_font)
    draw.text((350, y + 10), "Finding", fill="black", font=table_header_font)
    draw.text((900, y + 10), "Status", fill="black", font=table_header_font)

    # Finding rows
    findings = [
        ("CRITICAL", "Data Loss", "High Failure Rate for splunk_hec", "#d32f2f"),
        ("HIGH", "Security", "Default admin password is in use", "#ff6f00"),
        ("MEDIUM", "Performance", "Load Distribution: Traffic is imbalanced", "#fbc02d"),
    ]

    y = 150
    for severity, category, title, color in findings:
        # Row background
        draw.rectangle([50, y, 1100, y + 60], outline="lightgray", width=1)

        # Severity badge
        draw.rectangle([60, y + 10, 130, y + 30], fill=color, outline=color)
        draw.text((65, y + 12), severity, fill="white", font=table_header_font)

        # Category and title
        draw.text((150, y + 10), category, fill="black", font=text_font)
        draw.text((350, y + 10), title[:60] + "...", fill="black", font=text_font)

        # Status
        draw.text((900, y + 10), "Review", fill="blue", font=text_font)

        y += 70

    # Add footer note
    try:
        footer_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except (OSError, IOError):
        footer_font = ImageFont.load_default()
    draw.text(
        (50, 950),
        "For detailed remediation steps, click on each finding",
        fill="gray",
        font=footer_font,
    )

    return img


def screenshot_5_branding_manager() -> Image.Image:
    """
    Screenshot 5: Branding/settings page
    Shows: Branding form with company name, logo upload, color picker, save button
    """
    img = Image.new("RGB", (1200, 800), color="white")
    draw = ImageDraw.Draw(img)

    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except (OSError, IOError):
        header_font = ImageFont.load_default()

    # Title
    draw.text((50, 30), "Branding Settings", fill="black", font=header_font)

    # Form sections
    y_pos = 120

    # Company Name
    draw_input_field(draw, 50, y_pos, 500, 40, "Company Name", "Mock Corp")

    # Logo Upload
    y_pos += 80
    draw.rectangle([50, y_pos, 250, y_pos + 100], outline="gray", fill="#f9f9f9")
    try:
        upload_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except (OSError, IOError):
        upload_font = ImageFont.load_default()
    draw.text((80, y_pos + 35), "📁 Upload Logo", fill="gray", font=upload_font)
    draw.text((50, y_pos - 20), "Logo", fill="black", font=upload_font)

    # Primary Color
    y_pos += 150
    draw.rectangle([50, y_pos, 150, y_pos + 50], fill="#2196F3", outline="gray", width=2)
    draw.text((50, y_pos - 20), "Primary Color", fill="black", font=upload_font)

    # Secondary Color
    draw.rectangle([200, y_pos, 300, y_pos + 50], fill="#4CAF50", outline="gray", width=2)
    draw.text((200, y_pos - 20), "Secondary Color", fill="black", font=upload_font)

    # Accent Color
    draw.rectangle([350, y_pos, 450, y_pos + 50], fill="#FF9800", outline="gray", width=2)
    draw.text((350, y_pos - 20), "Accent Color", fill="black", font=upload_font)

    # Save button
    y_pos += 120
    draw_button(draw, 50, y_pos, 150, 40, "Save Settings", "green")

    return img


def generate_mock_screenshots(theme_label: str):
    """Generate all 5 mock screenshots and save them."""
    screenshots_dir = Path(__file__).parent / "screenshots" / theme_label
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating mock screenshots ({theme_label})...")

    # Generate and save each screenshot
    screenshots = [
        ("credential_input.png", screenshot_1_credential_input, "Credentials entry page"),
        (
            "credential_test_success.png",
            screenshot_2_credential_test_success,
            "Successful connection test",
        ),
        ("analysis_completion.png", screenshot_3_analysis_completion, "Analysis summary"),
        ("review_analysis_full.png", screenshot_4_review_analysis_full, "Full analysis report"),
        ("branding_manager.png", screenshot_5_branding_manager, "Branding settings"),
    ]

    for filename, generator_func, description in screenshots:
        img = generator_func()
        filepath = screenshots_dir / filename
        img.save(filepath)
        print(f"✓ Generated {theme_label}/{filename} - {description}")

    print(f"\n✓ All screenshots saved to {screenshots_dir}")
    return screenshots_dir


# ============================================================================
# PART 3: Playwright Automation (For Future Use)
# ============================================================================


async def async_capture_screenshots():
    """
    Real Playwright automation for actual browser screenshots.

    Captures both light and dark mode screenshots, using mocked API responses.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: Playwright not installed. Run: pip install playwright")
        print("Then: npx playwright install chromium")
        return None

    screenshots_dir = Path(__file__).parent / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    storage_key = "cribl-hc-theme"
    analysis_id = "analysis-1234"

    credentials = [
        {
            "name": "prod",
            "url": "https://prod.cribl.cloud",
            "auth_type": "bearer",
            "has_token": True,
            "has_oauth": False,
            "client_id": None,
        }
    ]

    analyses = [
        {
            "analysis_id": analysis_id,
            "deployment_name": "prod",
            "status": "completed",
            "created_at": "2026-01-11T03:00:00Z",
            "started_at": "2026-01-11T03:01:00Z",
            "completed_at": "2026-01-11T03:03:00Z",
            "analyzers": ["worker_group_balance", "endpoint_health", "security", "config"],
            "progress_percent": 100,
            "current_step": None,
            "api_calls_used": 42,
        }
    ]

    findings = [
        {
            "id": "traffic-imbalance",
            "category": "Performance",
            "severity": "medium",
            "title": "Load Distribution: Traffic is imbalanced across worker groups",
            "description": "The Gini coefficient is above threshold.",
            "affected_components": ["worker_group_balance"],
            "remediation_steps": ["Review routing rules to balance load."],
            "product_tags": ["stream"],
            "worker_group": None,
            "grouping_id": None,
        },
        {
            "id": "high-failure-rate-splunk",
            "category": "Data Loss",
            "severity": "critical",
            "title": "High Failure Rate for splunk_hec",
            "description": "Failure rate exceeds 15%.",
            "affected_components": ["endpoint_health"],
            "remediation_steps": ["Check downstream endpoint health."],
            "product_tags": ["stream"],
            "worker_group": None,
            "grouping_id": None,
        },
        {
            "id": "default-admin-password",
            "category": "Security",
            "severity": "high",
            "title": "Default admin password is in use",
            "description": "The default admin password is still configured.",
            "affected_components": ["security"],
            "remediation_steps": ["Rotate admin credentials immediately."],
            "product_tags": ["stream"],
            "worker_group": None,
            "grouping_id": None,
        },
    ]

    analysis_results = {
        "analysis_id": analysis_id,
        "deployment_name": "prod",
        "status": "completed",
        "health_score": 78,
        "findings_count": 3,
        "findings": findings,
        "recommendations_count": 0,
        "completed_at": "2026-01-11T03:03:00Z",
        "duration_seconds": 120,
        "version_info": {
            "leader_version": "4.6.0",
            "product_type": "stream",
            "product_versions": {"stream": "4.6.0"},
            "component_versions": [],
        },
        "summary": {
            "total_findings": 3,
            "critical_count": 1,
            "high_count": 1,
            "medium_count": 1,
            "low_count": 0,
            "info_count": 0,
            "health_score": 78,
            "risk_level": "high",
            "categories": {"Data Loss": 1, "Security": 1, "Performance": 1},
        },
    }

    branding_config = {
        "provider": {
            "name": "Cribl Partner",
            "tagline": "Observability for Everyone",
            "contact_email": "support@cribl.io",
        },
        "client": {
            "name": "Mock Corp",
            "report_title": "Mock Corp Health Analysis",
        },
        "theme": {
            "default_mode": "system",
            "light": {
                "primary": "#00A3E0",
                "primary_hover": "#0082B3",
                "primary_foreground": "#FFFFFF",
                "secondary": "#0066A1",
                "secondary_hover": "#005080",
                "secondary_foreground": "#FFFFFF",
                "accent": "#FFB81C",
                "accent_hover": "#E6A619",
                "accent_foreground": "#1F2937",
                "background": "#FFFFFF",
                "background_secondary": "#F9FAFB",
                "background_tertiary": "#F3F4F6",
                "foreground": "#111827",
                "foreground_secondary": "#4B5563",
                "foreground_muted": "#9CA3AF",
                "border": "#E5E7EB",
                "border_focus": "#00A3E0",
                "severity_critical": "#DC2626",
                "severity_high": "#EA580C",
                "severity_medium": "#F59E0B",
                "severity_low": "#3B82F6",
                "severity_info": "#6B7280",
                "success": "#10B981",
                "warning": "#F59E0B",
                "error": "#EF4444",
            },
            "dark": {
                "primary": "#00A3E0",
                "primary_hover": "#33B5E7",
                "primary_foreground": "#FFFFFF",
                "secondary": "#0066A1",
                "secondary_hover": "#3385B5",
                "secondary_foreground": "#FFFFFF",
                "accent": "#FFB81C",
                "accent_hover": "#FFC94D",
                "accent_foreground": "#1F2937",
                "background": "#111827",
                "background_secondary": "#1F2937",
                "background_tertiary": "#374151",
                "foreground": "#F9FAFB",
                "foreground_secondary": "#D1D5DB",
                "foreground_muted": "#6B7280",
                "border": "#374151",
                "border_focus": "#00A3E0",
                "severity_critical": "#F87171",
                "severity_high": "#FB923C",
                "severity_medium": "#FBBF24",
                "severity_low": "#60A5FA",
                "severity_info": "#9CA3AF",
                "success": "#34D399",
                "warning": "#FBBF24",
                "error": "#F87171",
            },
            "border_radius": "0.5rem",
            "border_radius_lg": "0.75rem",
        },
        "report": {
            "show_provider_logo": True,
            "show_client_logo": True,
            "show_footer": True,
            "show_watermark": False,
        },
    }

    async def setup_mock_routes(page):
        async def handle_route(route, request):
            url = request.url
            method = request.method

            if url.endswith("/api/v1/credentials") and method == "GET":
                await route.fulfill(json=credentials)
                return
            if "/api/v1/credentials/" in url and url.endswith("/test") and method == "POST":
                await route.fulfill(
                    json={
                        "success": True,
                        "message": "Connection successful!",
                        "cribl_version": "4.6.0",
                        "response_time_ms": 120,
                        "error": None,
                    }
                )
                return
            if url.endswith("/api/v1/analysis") and method == "GET":
                await route.fulfill(json=analyses)
                return
            if "/api/v1/analysis/" in url and url.endswith("/results") and method == "GET":
                await route.fulfill(json=analysis_results)
                return
            if url.endswith("/api/v1/branding") and method == "GET":
                await route.fulfill(json=branding_config)
                return

            await route.fulfill(status=404, json={"detail": "Not mocked"})

        await page.route("**/api/v1/**", handle_route)

    print("Launching browser for actual screenshot capture...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for theme_label, theme_value in [("light", "light"), ("dark", "dark")]:
            theme_dir = screenshots_dir / theme_label
            theme_dir.mkdir(parents=True, exist_ok=True)

            context = await browser.new_context(viewport={"width": 1200, "height": 800})
            await context.add_init_script(f"localStorage.setItem('{storage_key}', '{theme_value}')")
            page = await context.new_page()
            await setup_mock_routes(page)

            try:
                # Screenshot 1: Credentials Page (with modal open)
                print(f"Navigating to credentials page ({theme_label})...")
                await page.goto("http://localhost:5173/credentials")
                await page.wait_for_selector('button:has-text("Add Credential")')
                await page.click('button:has-text("Add Credential")')
                await page.wait_for_selector('input[placeholder="my-cribl-deployment"]')
                await page.screenshot(path=str(theme_dir / "credential_input.png"), full_page=False)
                print(f"✓ {theme_label}/credential_input.png")

                # Close modal so we can access credential card
                await page.click('button:has-text("Cancel")')
                await page.wait_for_timeout(500)

                # Screenshot 2: Test Credentials Success (toast)
                await page.wait_for_selector('button[title="Test connection"]')
                await page.click('button[title="Test connection"]')
                await page.wait_for_selector("text=Connection successful!")
                await page.screenshot(
                    path=str(theme_dir / "credential_test_success.png"), full_page=False
                )
                print(f"✓ {theme_label}/credential_test_success.png")

                # Screenshot 3: Analysis Page
                print(f"Navigating to analysis page ({theme_label})...")
                await page.goto("http://localhost:5173/analysis")
                await page.wait_for_selector("text=Health Check Analyses")
                await page.screenshot(
                    path=str(theme_dir / "analysis_completion.png"), full_page=False
                )
                print(f"✓ {theme_label}/analysis_completion.png")

                # Screenshot 4: Results Page
                print(f"Navigating to results page ({theme_label})...")
                await page.goto(f"http://localhost:5173/results/{analysis_id}")
                await page.wait_for_selector("text=Analysis ID")
                await page.screenshot(
                    path=str(theme_dir / "review_analysis_full.png"), full_page=True
                )
                print(f"✓ {theme_label}/review_analysis_full.png")

                # Screenshot 5: Branding Page
                print(f"Navigating to branding page ({theme_label})...")
                await page.goto("http://localhost:5173/branding")
                await page.wait_for_selector("text=Branding Settings")
                await page.screenshot(path=str(theme_dir / "branding_manager.png"), full_page=False)
                print(f"✓ {theme_label}/branding_manager.png")

            finally:
                await context.close()

        await browser.close()

    print(f"\n✓ All screenshots saved to {screenshots_dir}")
    return screenshots_dir


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Cribl Health Check - Screenshot Generation")
    print("=" * 70)

    # Generate real screenshots with Playwright (fallback to mock on failure)
    try:
        screenshot_dir = asyncio.run(async_capture_screenshots())
    except Exception as exc:
        print("Playwright capture failed; falling back to mock screenshots.")
        print(f"Reason: {exc}")
        for theme_label in ["light", "dark"]:
            generate_mock_screenshots(theme_label)
        screenshot_dir = Path(__file__).parent / "screenshots"

    print("\n" + "=" * 70)
    print("SELECTOR REFERENCE (For Playwright Automation)")
    print("=" * 70)
    print(json.dumps(SELECTORS, indent=2))

    print("\n" + "=" * 70)
    print("RUN NOTES")
    print("=" * 70)
    print("""
This run uses Playwright against the live frontend.

Prerequisites:
1. Playwright browser installed:
   $ npx playwright install chromium
2. Frontend dev server running:
   $ cd /Projects/cribl-hc/frontend
   $ npm run dev
""")

    print(f"\n✓ Screenshots ready at: {screenshot_dir}")
