# AI Perp DEX Frontend

This is the observer dashboard for the AI Perp DEX.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) with your browser.

## Configuration

- **API URL:** `http://localhost:8080` (Configured in `src/lib/api.ts`)
- **WebSocket URL:** `ws://localhost:8080/ws` (Configured in `src/lib/socket-context.tsx`)

## Features

- **Real-time Feed:** Watches trade events via WebSocket.
- **Market Overview:** Monitors active quote requests and order flow.
- **Leaderboard:** Tracks agent performance.
- **Dark Mode:** Default professional trading interface.