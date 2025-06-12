# User Interface Strategy for Managing Archival Collections

To improve usability, we can remove the dependency on Google Sheets and instead provide a dedicated user interface for creating and managing collections of URLs to archive. The centerpiece of this UI is an Excel-like sheet where users can type in URLs just as they would in a spreadsheet. The sheet should store data persistently so collections can be saved and loaded across sessions.

The following steps outline a possible approach.

## 1. Deprecate Google Sheets Integration

1. Mark the current `gsheet_feeder_db` module as deprecated in the documentation.
2. Provide migration tools to export existing sheets to a format accepted by the new interface (e.g. CSV or JSON).
3. Remove references to Google Sheets from the default configuration.

## 2. Build a Web-Based Collection Manager

1. **Frontend**: A single-page application built with React or a lightweight framework. It should allow users to:
   - Create, edit and delete collections of URLs.
   - Enter URLs directly into an Excel-like grid that supports sorting and filtering.
   - Persist and reload the grid contents between sessions.
   - Optionally import or export data from CSV files.
   - Start archiving jobs and monitor progress.
   
   The Excel-style grid is the primary way users enter and edit URLs. Changes
   are saved automatically so the sheet can be reloaded later without losing
   data.
2. **Backend**: Extend the current `ArchivingOrchestrator` with a simple REST API. This API should expose endpoints to:
   - List, create and update collections.
   - Trigger archiving for a collection.
   - Query the status of archival tasks.
3. **Storage**: Use the existing database modules (CSV, SQLite, etc.) for persistence, but abstract them behind the API so the UI does not depend on any particular storage backend.

## 3. Update Documentation and Examples

1. Replace Google Sheets setup guides with instructions for the web interface.
2. Provide screenshots or a demo video of the new UI workflow.
3. Offer migration tips for users coming from Google Sheets.

## 4. Incremental Rollout

1. Release the first version of the UI alongside the existing command-line tools.
2. Encourage feedback and iterate on the interface and features.
3. Once stable, fully remove the Google Sheets integration from the codebase.

By focusing on a dedicated interface for managing collections, users can work entirely within the app without relying on third‑party spreadsheets, improving the overall experience.
