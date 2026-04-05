# SudoPHASE Web Deployment

Quick start guide for deploying the Sudoku solver as a web application.

## Quick Start

### 1. Install Backend Dependencies

```bash
cd web-deployment
npm init -y
npm install express cors
```

### 2. Update Solver Path

Edit `examples/backend-example.js` and update the `solverPath` variable to point to your compiled solver executable:

```javascript
// Windows example:
const solverPath = path.join(__dirname, '../../vs2017/x64/Release/sudoku_ants.exe');

// Linux example:
const solverPath = path.join(__dirname, '../../sudokusolver');
```

### 3. Start Backend Server

```bash
node examples/backend-example.js
```

Server will run on http://localhost:3001

### 4. Open Frontend

Open `examples/frontend-example.html` in a web browser (or serve via a local web server).

### 5. Test

Enter a puzzle string and click "Solve Puzzle"!

## Example Puzzle String

```
53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79
```

(Use `.` for empty cells)

## Production Deployment

See `WEB_DEPLOYMENT_GUIDE.md` for complete deployment instructions including:
- Docker setup
- Cloud platform deployment
- Security considerations
- Performance optimization

## API Endpoint

### POST /api/solve

**Request:**
```json
{
    "puzzle": "53..7....6..195....98....6...",
    "algorithm": 2,
    "timeout": 120,
    "params": {
        "subcolonies": 4,
        "ants": 30
    }
}
```

**Response:**
```json
{
    "success": true,
    "solution": "...",
    "time": 14.523,
    "iterations": 1247
}
```


















