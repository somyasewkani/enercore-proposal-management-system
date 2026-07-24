---
name: Enercore Solar Business Portal
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#3f4a3d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#6f7a6b'
  outline-variant: '#bfcab9'
  surface-tint: '#006e1c'
  primary: '#006b1b'
  on-primary: '#ffffff'
  primary-container: '#268630'
  on-primary-container: '#f7fff1'
  inverse-primary: '#7ddc7a'
  secondary: '#8f4e00'
  on-secondary: '#ffffff'
  secondary-container: '#ff8f06'
  on-secondary-container: '#623300'
  tertiary: '#005ea4'
  on-tertiary: '#ffffff'
  tertiary-container: '#0077ce'
  on-tertiary-container: '#fdfcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#98f994'
  primary-fixed-dim: '#7ddc7a'
  on-primary-fixed: '#002204'
  on-primary-fixed-variant: '#005313'
  secondary-fixed: '#ffdcc2'
  secondary-fixed-dim: '#ffb77b'
  on-secondary-fixed: '#2e1500'
  on-secondary-fixed-variant: '#6d3a00'
  tertiary-fixed: '#d3e4ff'
  tertiary-fixed-dim: '#a2c9ff'
  on-tertiary-fixed: '#001c38'
  on-tertiary-fixed-variant: '#004881'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-max: 1440px
  gutter: 24px
  margin-desktop: 40px
  margin-tablet: 24px
  margin-mobile: 16px
---

## Brand & Style

The design system is engineered for a high-stakes enterprise environment where solar energy experts and business developers manage complex data. The brand personality is **authoritative yet forward-thinking**, blending the stability of established energy sectors with the agility of AI-driven technology.

The visual style is **Corporate Modern with a Glassmorphic edge**. It utilizes a "Clean Canvas" philosophy: expansive white backgrounds provide a neutral stage for data-rich glassmorphic containers. These containers use subtle transparency and backdrop blurs to create depth without visual clutter. The aesthetic should feel precision-engineered, echoing the technical accuracy required in solar proposals.

**Key visual principles:**
- **Clarity over Decoration:** Every visual element must serve a functional purpose in data interpretation.
- **Sustainable Sophistication:** Use of organic greens and energy-rich oranges balanced by cool, technical blues.
- **Architectural Depth:** Layering is achieved through varying degrees of translucency rather than heavy shadows.

## Colors

The color palette is derived directly from the core brand identity, optimized for digital accessibility. 

- **Primary Green (#43A047):** Used for primary actions, success states, and representing "Sustainability" and "Growth."
- **Secondary Orange (#FB8C00):** Used for highlights, critical notifications, and representing "Energy" and "Activity."
- **UI Blue (#1E88E5):** Acts as the functional workhorse for interactive elements, navigation links, and informational charts, providing a professional SaaS feel.
- **Neutral Palette:** Utilizes a range of cool slates and greys (from #F8FAFC to #1E293B) to maintain a crisp, airy environment. 

Backgrounds should remain predominantly white (#FFFFFF) to maximize contrast for the glassmorphic card effects and technical data tables.

## Typography

This design system employs **Inter** exclusively to ensure maximum legibility across high-density data visualizations and technical documentation. 

The type scale is designed for an enterprise hierarchy:
- **Headlines:** Use semi-bold and bold weights with tighter letter spacing to create a sense of grounded authority.
- **Body Text:** Standardized at 16px for optimal reading comfort.
- **Labels:** Utilized for chart legends and table headers, often in uppercase with slight tracking to differentiate them from actionable text.
- **Numbers:** When used in dashboards, numbers should leverage Inter’s tabular lining features to ensure columns of figures align perfectly.

## Layout & Spacing

The layout follows a **structured fluid grid** model. On desktop, a 12-column grid is used with 24px gutters to allow for significant whitespace between complex data widgets.

**Layout Philosophy:**
- **Sidebar Navigation:** A fixed 280px sidebar provides persistent access to core modules.
- **The "Stage":** The main content area uses a maximum width of 1440px to prevent line lengths from becoming unreadable on ultra-wide monitors.
- **Modular Widgets:** Dashboard components should snap to a 4-column, 6-column, or 12-column width.
- **Padding:** Generous internal padding (32px) within cards and containers is required to maintain the "premium" feel and avoid data density fatigue.

## Elevation & Depth

Depth in this design system is conveyed through **backlight and translucency** rather than traditional physical shadows.

- **Level 1 (Base):** The main background surface (#FFFFFF).
- **Level 2 (Cards):** Glassmorphic surfaces with `backdrop-filter: blur(20px)` and a thin 1px border of `rgba(255, 255, 255, 0.4)`.
- **Level 3 (Interactive/Hover):** When a card or element is hovered, the backdrop blur increases and a soft, low-opacity ambient shadow (#1E88E5 at 8% opacity) is applied to signify lift.
- **Level 4 (Modals/Overlays):** These use a higher elevation with a darker backdrop tint to focus the user’s attention on the critical task at hand.

## Shapes

The shape language is **Refined and Rounded**. By using a radius of 0.5rem (8px) for standard UI elements and 1.5rem (24px) for major dashboard cards, the interface feels approachable and modern while maintaining enough structure for a professional portal.

- **Input Fields & Buttons:** 8px radius.
- **Dashboard Cards:** 16px to 24px radius depending on the scale of the widget.
- **Status Chips:** Full pill-shape (100px radius) to distinguish them from actionable buttons.

## Components

### Buttons
Primary buttons use a solid Green (#43A047) fill with white text. Secondary buttons use a UI Blue (#1E88E5) ghost style with a 1px border. All buttons have a height of 44px for high tap-targets.

### Dashboard Widgets (Glassmorphic)
Cards are the primary container. They feature a semi-transparent white background, a 20px backdrop blur, and a subtle white inner border. Titles within widgets are always semi-bold Inter at 18px.

### Data Tables
Tables should have no outer borders, using only horizontal dividers in a light Slate (#E2E8F0). Header rows use the `label-md` typography style for clarity.

### Interactive Charts
Charts should utilize the primary Green and UI Blue for data series. Secondary Orange is reserved strictly for outliers, goals, or warning thresholds within the data.

### Sidebar Navigation
The sidebar is dark-themed or very high-contrast light to separate it from the content stage. Active states are indicated by a 4px Green vertical bar on the left edge and a subtle tint behind the menu item.

### File Upload Areas
Large, dashed-border areas with a 16px radius. When a file is hovered over the area, the border color shifts to Primary Green and the background becomes slightly more opaque.