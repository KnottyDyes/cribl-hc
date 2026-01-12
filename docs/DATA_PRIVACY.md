# Data Privacy & Governance Standards

## Core Philosophy: "Touch and Drop"

The Cribl Health Check tool operates under a strict **Zero-Persistence Policy** regarding customer event data. While the tool requires access to live data planes to perform advanced analysis (like PII detection or latency monitoring), it treats all event data as **transient and temporal**.

We distinguish strictly between **Content** (Customer Data) and **Metadata** (Configuration & Health Metrics).

- **Content** is processed in-memory and immediately discarded.
- **Metadata** is aggregated, anonymized, and reported.

## Data Handling by Feature

### 1. Sensitive Data Scanning (PII/PCI Detection)
This analyzer samples live data to detect unmasked secrets or sensitive information.

- **Process**:
    1. Fetches a small sample (e.g., 50 events) into volatile memory (RAM).
    2. Runs regex pattern matching against these objects.
    3. Calculates aggregate counts (e.g., "Found 5 potential SSNs").
    4. **IMMEDIATELY DISCARDS** the raw event objects from memory.
- **Persistence**:
    - **Stored**: Pattern types (e.g., "SSN", "Credit Card") and match counts.
    - **NEVER Stored**: The actual matched strings, surrounding text, or raw event payloads.

### 2. Freshness & Latency Monitoring
This analyzer calculates the time delta between event generation (`_time`) and processing (`now`).

- **Process**:
    1. Fetches sample events into RAM.
    2. Extracts the `_time` field (epoch timestamp).
    3. Computes `lag = now - _time`.
    4. Discards the event object.
- **Persistence**:
    - **Stored**: Aggregate metrics (Max Lag, Average Lag in seconds).
    - **NEVER Stored**: Raw timestamps or event content.

### 3. Schema Drift Detection (Planned)
To detect unexpected changes in data shape, we must track schema state over time.

- **Process**:
    1. Fetches sample events into RAM.
    2. Derives a **Structural Fingerprint** (Map of `Field Name` → `Data Type`).
    3. Discards the event object.
    4. Persists the Fingerprint to a local state file for future comparison.
- **Persistence**:
    - **Stored**: Field names (`user_agent`, `status_code`) and types (`string`, `number`).
    - **NEVER Stored**: Field values (e.g., "Mozilla/5.0", "404").

## Storage Standards: Allowlist vs Blocklist

To ensure compliance with SOC2, HIPAA, and GDPR requirements, the tool enforces the following storage boundaries:

| Data Type | Memory (RAM) | Persistence (Disk/Reports) | Example |
|-----------|--------------|----------------------------|---------|
| **Raw Event Payload** | ✅ Temporary | ❌ **FORBIDDEN** | `{"user": "jdoe", "ssn": "123..."}` |
| **Field Values** | ✅ Temporary | ❌ **FORBIDDEN** | `"jdoe"`, `"10.0.0.1"` |
| **Field Structure** | ✅ Allowed | ✅ Allowed | `user: string`, `ip: ipv4` |
| **Aggregate Metrics** | ✅ Allowed | ✅ Allowed | `lag: 5.2s`, `count: 100` |
| **Pattern Matches** | ✅ Temporary | ❌ **FORBIDDEN** | The actual SSN string detected |
| **Pattern Counts** | ✅ Allowed | ✅ Allowed | "Found 3 SSN patterns" |

## Compliance Statement

This tool is designed to function as a **transient processor**. It does not act as a data store or log archive.

- **No Logging of Paylogs**: Debug logs (`--debug`) utilize structured logging that explicitly excludes raw event dictionaries.
- **No Remediation Persistence**: The tool suggests remediation but does not modify data streams or store "fixed" versions of data.
- **Secure by Default**: All data plane features requiring sampling must be explicitly enabled via specific analyzer flags.
