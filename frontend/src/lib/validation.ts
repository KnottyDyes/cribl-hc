import { z } from 'zod'

export const serviceProviderBrandingSchema = z.object({
  name: z.string().min(1, 'Organization name is required'),
  contact_email: z.string().email('Invalid email address').optional().or(z.literal('')),
  website: z.string().url('Invalid URL').optional().or(z.literal('')),
  tagline: z.string().max(100, 'Tagline must be 100 characters or less').optional(),
  footer_text: z.string().max(500, 'Footer text must be 500 characters or less').optional(),
  logo_path: z.string().optional(),
  logo_path_dark: z.string().optional(),
  logo_url: z.string().url().optional().or(z.literal('')),
  logo_url_dark: z.string().url().optional().or(z.literal('')),
  primary_color: z.string().optional(),
  secondary_color: z.string().optional(),
})

export const clientBrandingSchema = z.object({
  name: z.string().min(1, 'Client name is required'),
  identifier: z.string().optional(),
  report_title: z.string().optional(),
  logo_path: z.string().optional(),
  logo_path_dark: z.string().optional(),
  logo_url: z.string().url().optional().or(z.literal('')),
  logo_url_dark: z.string().url().optional().or(z.literal('')),
})

const colorSchema = z.string().regex(/^#([0-9a-f]{3}){1,2}$/i, 'Invalid hex color')

const themeColorsSchema = z.object({
    primary: colorSchema,
    primary_hover: colorSchema,
    primary_foreground: colorSchema,
    secondary: colorSchema,
    secondary_hover: colorSchema,
    secondary_foreground: colorSchema,
    accent: colorSchema,
    accent_hover: colorSchema,
    accent_foreground: colorSchema,
    background: colorSchema,
    background_secondary: colorSchema,
    background_tertiary: colorSchema,
    foreground: colorSchema,
    foreground_secondary: colorSchema,
    foreground_muted: colorSchema,
    border: colorSchema,
    border_focus: colorSchema,
    severity_critical: colorSchema,
    severity_high: colorSchema,
    severity_medium: colorSchema,
    severity_low: colorSchema,
    severity_info: colorSchema,
    success: colorSchema,
    warning: colorSchema,
    error: colorSchema,
})

export const uiThemeSchema = z.object({
  default_mode: z.enum(['light', 'dark', 'system']),
  light: themeColorsSchema,
  dark: themeColorsSchema,
  font_family: z.string().optional(),
  font_family_mono: z.string().optional(),
  border_radius: z.string(),
  border_radius_lg: z.string(),
})

export const reportBrandingSchema = z.object({
  show_provider_logo: z.boolean(),
  show_client_logo: z.boolean(),
  show_footer: z.boolean(),
  show_watermark: z.boolean(),
  watermark_text: z.string().optional(),
  custom_css: z.string().optional(),
  header_template: z.string().optional(),
  footer_template: z.string().optional(),
})
