# Instructions: Build a Scriptable Widget for Food Tracker

## Goal

Create a beautiful, large-size iOS widget using the **Scriptable** app. The widget should visualize daily nutrition progress based on JSON data fetched from an API.

## API Specification

- **Endpoint**: `GET <HOST>/v1/widget/today`
- **Authentication (preferred)**: `X-API-Key: <APP_GENERATED_KEY>`
- **Alternative**: `Authorization: Bearer <APP_GENERATED_KEY>`
- **Legacy fallback**: `Authorization: Bearer <WIDGET_API_TOKEN>` (only if `WIDGET_API_TOKEN` is configured)
- **Response Format**:
  ```json
  {
    "generated_at": "2026-02-18T23:33:05.906723",
    "timezone": "Europe/Berlin",
    "day": {
      "date": "2026-02-18",
      "total_kcal": 1500.0,
      "total_protein": 120.0,
      "total_carbs": 150.0,
      "total_fat": 60.0,
      "entry_count": 5
    },
    "week": {
      "total_kcal": 10500.0,
      "days_tracked": 7
    },
    "streak": 12
  }
  ```

## Requirements

### 1. Data Fetching

- Fetch data from the API with a timeout (e.g., 3s).
- Use `Keychain` or a config variable to store the `HOST` and auth secret.
- Use `Keychain` or a config variable to store the `HOST` and `API key`.
- **Offline Handling**: If the request fails, load the last successful response from `FileManager` (local cache) and show a "stale data" indicator (e.g., grayed out or a small warning icon).

### 2. Visualization

- **Layout**: Use `ListWidget` (Large or Medium size).
- **Header**:
  - Show "Today" date.
  - Show current Streak ("🔥 12").
- **Main Stats (Calories)**:
  - Big bold number for Kcal consumed.
  - Progress bar relative to a target (e.g., 2500 kcal - make this configurable).
- **Macros (Protein, Carbs, Fat)**:
  - Three columns or rows.
  - Each with a label, value (g), and a small progress bar.
  - Colors:
    - Protein: Blue/Indigo
    - Carbs: Green/Teal
    - Fat: Orange/Red

### 3. Design Aesthetics

- **Theme**: Dark mode preferred (dark gray background, vibrant colors for bars).
- **Fonts**: Use system rounded fonts (`Font.roundedSystemFont(size)`).
- **Spacing**: Ensure sufficient padding so it doesn't look crowded.

### 4. Code Structure

- Keep `const config = { ... }` at the top for easy user customization (Base URL, Token, Targets).
  ```javascript
  const config = {
    baseUrl: "http://<YOUR_PI_IP>:8787",
    apiKey: "ftk_...",
    targetKcal: 2500,
  };
  ```
- Implement a helper function `fetchData()` that handles the fallback logic.
- Implement a helper `createProgress(width, height, percent, color)` to draw bars using `DrawContext` (if needed) or simple text/rectangles.
