# Frontend Documentation

## Overview
The frontend is a Next.js application using the App Router architecture. It provides a dashboard for monitoring camera streams, managing vehicle registrations, and viewing history logs.

## Tech Stack
- **Framework**: Next.js (App Router)
- **Language**: TypeScript (`.tsx`, `.ts`)
- **Styling**: Tailwind CSS (presumed based on typical stack) or CSS Modules
- **State Management**: React Hooks

## Folder Structure
- `frontend/app/`: App Router pages and layouts.
  - `(dashboard)/`: Protected dashboard routes.
    - `manage-cars/`: Vehicle registration management.
    - `history/`: View entry/exit logs.
    - `camera/`: Camera stream monitoring.
    - `settings/`: System configuration.
- `frontend/components/`: Reusable UI components.
- `frontend/services/`: API integration services (communicating with Backend).

## Key Features
1.  **Monitor Dashboard**: Real-time view of camera streams.
2.  **Vehicle Management**: CRUD operations for registered vehicles.
3.  **History Log**: Filterable table of past vehicle events.
4.  **Camera Configuration**: Settings to add/remove/edit camera streams.

## API Integration
The frontend communicates with the backend via REST API calls. ensure the Base URL is configured in `.env` or configuration files.
