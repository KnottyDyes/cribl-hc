# Future Features

This document tracks feature requests and enhancements planned for future releases of cribl-hc.

## Report Branding and Customization

**Priority:** Post-MVP Enhancement
**Phase:** TBD (after Phase 7)
**Status:** Planned

### Overview

Add branding customization to generated reports (JSON, Markdown, HTML/PDF) to support:
1. **Service Provider Branding** - Company running the health check (e.g., MSP, consulting firm)
2. **Client Branding** - End customer receiving the report

### Use Cases

1. **Managed Service Providers (MSPs)**: Run health checks for multiple clients with MSP branding + client-specific branding
2. **Consulting Firms**: Deliver professional reports with consulting firm logo and client branding
3. **Internal IT Teams**: Customize reports for different business units or departments
4. **Multi-Tenant SaaS**: Generate branded reports for different organizations

### Proposed Features

#### Service Provider Branding
- Company name
- Logo (various formats: PNG, SVG, etc.)
- Company colors (primary, secondary, accent)
- Contact information (support email, website, phone)
- Footer text (company tagline, legal disclaimers)
- Custom CSS/styling for HTML/PDF reports

#### Client Branding
- Client name
- Client logo
- Client identifier (account number, department, etc.)
- Custom report title
- Client-specific disclaimer or notes section

#### Configuration Options

**Option 1: Configuration File**
```yaml
# ~/.cribl-hc/branding.yaml
service_provider:
  name: "Acme Consulting"
  logo: "/path/to/acme-logo.png"
  primary_color: "#1E88E5"
  contact_email: "support@acme.com"
  website: "https://acme.com"
  footer: "© 2025 Acme Consulting. All rights reserved."

clients:
  - id: "client-123"
    name: "Example Corp"
    logo: "/path/to/example-logo.png"
    account_number: "AC-123456"
```

**Option 2: CLI Flags**
```bash
cribl-hc analyze run \
  --provider-name "Acme Consulting" \
  --provider-logo acme-logo.png \
  --client-name "Example Corp" \
  --client-logo example-logo.png \
  --output branded-report.pdf
```

**Option 3: Deployment Profiles**
```bash
# Store branding with deployment config
cribl-hc config set prod \
  --url https://cribl.example.com \
  --token TOKEN \
  --provider-name "Acme Consulting" \
  --client-name "Example Corp"
```

### Report Output Examples

#### Markdown Report Header
```markdown
# Cribl Stream Health Check Report

**Prepared by:** Acme Consulting
**For:** Example Corp (Account: AC-123456)
**Date:** 2025-12-13
**Cribl Version:** 4.7.0

---
```

#### PDF Report Title Page
```
[Acme Consulting Logo]

Cribl Stream Health Check Report

Prepared for:
[Example Corp Logo]
Example Corp
Account: AC-123456

Prepared by:
Acme Consulting
support@acme.com
https://acme.com

Report Date: December 13, 2025
Cribl Version: 4.7.0

---
© 2025 Acme Consulting. All rights reserved.
```

### Implementation Considerations

1. **File Format Support**
   - Markdown: Text-based branding (company names, headers)
   - JSON: Metadata fields for branding
   - HTML: Full CSS/styling support
   - PDF: Logo embedding, custom styling

2. **Logo Handling**
   - Support common image formats (PNG, SVG, JPEG)
   - Auto-resize/scale for different output formats
   - Base64 encoding for embedded logos in HTML/PDF

3. **Constitution Compliance**
   - **Principle III (API-First)**: Branding should be configurable via API
   - **Principle VIII (Pluggable)**: Support custom report templates
   - **Principle X (Security)**: Don't expose sensitive branding info in logs

4. **Configuration Hierarchy**
   ```
   CLI flags > Deployment profile > Global config > Defaults
   ```

5. **Template System**
   - Support custom Jinja2/Mustache templates for reports
   - Provide default templates for each format
   - Allow users to override sections (header, footer, styling)

### Dependencies

- **Report Generator Refactor**: Move from inline formatting to template-based
- **HTML/PDF Generation**: May require additional libraries (e.g., WeasyPrint, ReportLab)
- **Image Processing**: PIL/Pillow for logo handling

### Related Features

- **Custom Report Templates** - Allow users to define their own report layouts
- **White-Label Mode** - Remove all cribl-hc branding for service providers
- **Multi-Language Reports** - i18n support for international clients
- **Report Themes** - Pre-built color schemes and layouts

### User Feedback

- **Sean Armstrong (Dec 13, 2025)**: "Add a task for the future, I want to be able to provide the ability to add branding for not only the company running the health check, but also for the client if we so choose."

### Acceptance Criteria (When Implemented)

- [ ] Support service provider branding (name, logo, contact info)
- [ ] Support client branding (name, logo, account identifier)
- [ ] Configuration via YAML file, CLI flags, and deployment profiles
- [ ] Branding applies to Markdown, JSON metadata, HTML, and PDF reports
- [ ] Logo embedding in HTML/PDF with auto-scaling
- [ ] Custom CSS/styling support for HTML/PDF
- [ ] Template override capability for advanced customization
- [ ] Documentation with examples for MSPs and consulting firms
- [ ] Unit tests for branding application in all formats
- [ ] Integration test with real logos and multi-client scenarios

---

**Last Updated:** December 13, 2025
**Tracking Issue:** TBD (create GitHub issue when prioritized)
