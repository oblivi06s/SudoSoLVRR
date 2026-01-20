# Sudoku Solver - Complete Code Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Core Modules](#core-modules)
4. [Solver Algorithms](#solver-algorithms)
5. [Friend Class Concept](#friend-class-concept)
6. [Data Flow](#data-flow)
7. [Design Decisions](#design-decisions)

---

## System Overview

This is a multi-threaded Sudoku puzzle solver using Ant Colony Optimization (ACO) algorithms. The system supports multiple solving strategies:

- **Algorithm 0**: Single-threaded Ant Colony System (ACS)
- **Algorithm 1**: Backtracking Search
- **Algorithm 2**: Multi-threaded ACS with communication (MultiThreadSudokuAntSystem)
- **Algorithm 3**: Multi-threaded Multi-Colony Ant System (MultiThreadMultiColonyAntSystem)

### Key Features
- Constraint propagation for initial puzzle reduction
- Multiple ACO variants (ACS and MMAS)
- Parallel execution with inter-thread communication
- Support for various puzzle sizes (6x6 to 64x64)

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      solvermain.cpp                          │
│              (Entry Point, Argument Parsing)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌────────▼──────────┐
│  SudokuSolver  │          │   BacktrackSearch  │
│   (Interface)  │          │                    │
└───────┬────────┘          └────────────────────┘
        │
   ┌────┴────┬──────────────────┬──────────────────┐
   │         │                  │                  │
┌──▼──┐  ┌───▼──────┐  ┌────────▼─────────┐  ┌─────▼──────────┐
│ ACS │  │ Multi-   │  │ Multi-Thread     │  │ Multi-Thread  │
│     │  │ Colony   │  │ Sudoku Ant       │  │ Multi-Colony   │
│     │  │ Ant      │  │ System           │  │ Ant System     │
└──┬──┘  │ System   │  └────────┬─────────┘  └─────┬──────────┘
   │     └───┬──────┘           │                   │
   │         │                  │                   │
   └─────────┴──────────────────┴───────────────────┘
              │                  │                   │
         ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
         │  Board  │        │  Board  │        │  Board  │
         │   +     │        │   +     │        │   +     │
         │   CP    │        │   CP    │        │   CP    │
         └─────────┘        └─────────┘        └─────────┘
```

---

## Core Modules

### 1. ValueSet (`valueset.h`, `valueset.cpp`)

**Purpose**: Efficient set representation using bitmaps for possible cell values.

**Key Features**:
- Uses 64-bit integers to represent sets of possible values
- Bitwise operations for set operations (union, intersection, difference)
- Optimized for Sudoku constraint checking

**Contribution to Solving**:
- Enables fast constraint checking (O(1) for many operations)
- Tracks which values are possible for each cell
- Used throughout constraint propagation

**Key Methods**:
- `Fixed()`: Returns true if exactly one value is possible
- `Empty()`: Returns true if no values are possible (infeasible)
- `Count()`: Returns number of possible values
- `Index()`: Returns the index of the fixed value
- Bitwise operators: `+` (union), `-` (difference), `^` (XOR), `~` (complement)

---

### 2. Board (`board.h`, `board.cpp`)

**Purpose**: Represents the Sudoku puzzle state and provides board operations.

**Key Responsibilities**:
- Stores the puzzle state (cells with their possible values)
- Provides accessor methods for cells, rows, columns, boxes
- Handles puzzle initialization from string format
- Delegates constraint propagation to CP module
- Validates solutions

**Data Members**:
```cpp
private:
    ValueSet *cells;           // Array of possible values for each cell
    int order;                 // Order of puzzle (for square grids)
    int boxRows, boxCols;      // Box dimensions
    int numUnits;              // Number of units (rows/cols/boxes)
    int numCells;              // Total number of cells
    int numFixedCells;         // Number of cells with unique values
    int numInfeasible;         // Number of cells with no possibilities
```

**Key Methods**:
- `SetCell(int i, const ValueSet &c)`: Sets a cell's value and triggers constraint propagation
- `GetCell(int i)`: Returns possible values for a cell
- `FixedCellCount()`: Returns number of fixed cells
- `CheckSolution(const Board& other)`: Validates if a solution is correct
- Helper methods: `RowCell()`, `ColCell()`, `BoxCell()`, `RowForCell()`, etc.

**Contribution to Solving**:
- Foundation data structure for all algorithms
- Maintains puzzle state throughout solving process
- Provides geometric operations (row/column/box access)

**Friend Class Relationship**:
```cpp
friend class CP;  // Allow CP to access private members
```

This allows CP to directly access `cells`, `numUnits`, `numInfeasible` for efficient constraint propagation.

---

### 3. CP - Constraint Propagation (`CP.h`, `CP.cpp`)

**Purpose**: Implements the constraint propagation algorithm for Sudoku.

**Key Responsibilities**:
- Applies Sudoku rules to eliminate impossible values
- Propagates constraints when a cell is set
- Detects infeasible states (cells with no possibilities)

**Why Separate Module?**
- **Separation of Concerns**: Board handles data, CP handles algorithm
- **Maintainability**: Constraint logic is isolated and easier to modify
- **Testability**: CP can be tested independently
- **Clarity**: Clear module boundaries

**Key Methods**:

#### `CP::ConstrainCell(Board& board, int cellIndex)`
**Purpose**: Applies constraint propagation to a single cell.

**Algorithm**:
1. **Skip if already fixed or empty**: Early exit for efficiency
2. **Identify constraints**: Find row, column, and box containing the cell
3. **Collect fixed values**: Gather all fixed values in the same row/column/box
4. **Calculate constraint set**: `fixedCellsConstraint = ~(rowFixed + colFixed + boxFixed)`
   - This gives all values that are NOT taken by fixed cells
5. **Apply constraints**:
   - If only one possibility remains → set the cell
   - Otherwise, eliminate taken values: `cells[i] ^= fixedCellsConstraint`
   - Check for "hidden singles": values that can only go in one place in a unit
6. **Detect infeasibility**: If cell becomes empty, increment `numInfeasible`

**Contribution to Solving**:
- Reduces search space before ACO algorithms run
- Automatically fills cells that have only one possibility
- Detects invalid puzzle states early
- Used every time a cell is set (via `Board::SetCell()`)

#### `CP::PropagateConstraints(Board& board, int cellIndex)`
**Purpose**: Propagates constraints to all affected cells after setting a cell.

**Algorithm**:
1. Find all cells in the same row, column, and box
2. Call `ConstrainCell()` for each affected cell
3. This creates a cascade effect: setting one cell may fix others

**Example**:
```
Setting cell (0,0) = 5 triggers:
- ConstrainCell for all cells in row 0
- ConstrainCell for all cells in column 0  
- ConstrainCell for all cells in box 0
```

**Contribution to Solving**:
- Maximizes constraint propagation efficiency
- Ensures all constraints are applied when state changes
- Critical for initial puzzle reduction

---

### 4. Timer (`timer.h`)

**Purpose**: High-resolution timing for performance measurement.

**Contribution to Solving**:
- Tracks solving time
- Enables timeout mechanisms
- Performance profiling

---

### 5. SudokuSolver (`sudokusolver.h`)

**Purpose**: Abstract base class defining the solver interface.

**Interface**:
```cpp
class SudokuSolver {
public:
    virtual bool Solve(const Board& puzzle, float maxTime) = 0;
    virtual float GetSolutionTime() = 0;
    virtual const Board& GetSolution() = 0;
};
```

**Contribution to Solving**:
- Polymorphism: Allows different algorithms to be used interchangeably
- Clean architecture: Separates interface from implementation
- Extensibility: Easy to add new solving algorithms

---

## Solver Algorithms

### Algorithm 0: SudokuAntSystem (`sudokuantsystem.h`, `sudokuantsystem.cpp`)

**Purpose**: Single-threaded Ant Colony System for Sudoku.

**Key Components**:
- `SudokuAnt`: Individual ant that constructs solutions
- Pheromone matrix: Guides ant decisions
- Local and global pheromone updates

**Algorithm Flow**:
1. Initialize pheromone matrix
2. For each iteration:
   - Each ant constructs a solution
   - Update local pheromone (as ant builds solution)
   - Find best solution in iteration
   - Update global pheromone (best-so-far)
3. Return best solution found

**Contribution to Solving**:
- Baseline ACO algorithm
- Foundation for more complex variants
- Demonstrates core ACO principles

---

### Algorithm 1: BacktrackSearch (`backtracksearch.h`, `backtracksearch.cpp`)

**Purpose**: Classic backtracking search with constraint propagation.

**Algorithm**:
1. Find cell with minimum remaining values (MRV heuristic)
2. Try each possible value:
   - Set cell and propagate constraints
   - Recursively solve remaining puzzle
   - If infeasible, backtrack
3. Return when all cells filled

**Contribution to Solving**:
- Exact algorithm (guaranteed to find solution if one exists)
- Useful for comparison with heuristic methods
- Demonstrates constraint propagation effectiveness

---

### Algorithm 2: MultiThreadSudokuAntSystem (`multithreadsudokuantsystem.h`, `multithreadsudokuantsystem.cpp`)

**Purpose**: Multi-threaded ACS with inter-thread communication.

**Architecture**:
- Multiple `SubColony` objects, each running in its own thread
- Each sub-colony maintains independent pheromone matrix
- Periodic communication via two topologies:
  - **Ring topology**: Iteration-best solutions
  - **Random topology**: Best-so-far solutions

**Key Classes**:

#### `SubColony`
**Purpose**: Represents one independent ant colony in a thread.

**Data Members**:
```cpp
int colonyId;                    // Unique identifier
float **pher;                    // Pheromone matrix [cell][value]
std::vector<SudokuAnt*> antList; // Ant population
Board iterationBest;              // Best solution this iteration
Board bestSol;                   // Best solution ever found
Board receivedIterationBest;      // Received from ring topology
Board receivedBestSol;            // Received from random topology
```

**Key Methods**:
- `RunIteration()`: Execute one iteration (construct solutions, evaluate, update)
- `UpdatePheromone()`: Standard ACS update (Algorithm 0 style)
- `UpdatePheromoneWithCommunication()`: Three-source update (local + 2 received)

**Contribution to Solving**:
- Parallel exploration of search space
- Diversity through independent colonies
- Knowledge sharing via communication

#### `MultiThreadSudokuAntSystem`
**Purpose**: Coordinates multiple sub-colonies and handles communication.

**Synchronization**:
- `std::mutex commMutex`: Protects communication operations
- `std::condition_variable commCV`: Coordinates barrier synchronization
- `std::atomic<int> barrier`: Tracks threads arriving at barrier
- `std::atomic<bool> stopFlag`: Signals all threads to stop

**Communication Topologies**:

1. **Ring Topology** (`CommunicateRingTopology()`):
   ```
   Colony 0 → Colony 1 → Colony 2 → ... → Colony N → Colony 0
   ```
   - Each colony sends its iteration-best to the next colony
   - Ensures every colony receives fresh information
   - Deterministic pattern

2. **Random Topology** (`CommunicateRandomTopology()`):
   - Colonies are randomly shuffled each communication cycle
   - Each colony receives best-so-far from its predecessor in shuffle
   - Provides diversity in information exchange

**Pheromone Update Strategy**:

**Standard Update** (non-communication iterations):
```cpp
τ_ij(t+1) = (1-ρ) · τ_ij(t) + ρ · Δτ_best
```
- Uses only local best-so-far solution
- ρ = 0.9 (standard ACS parameter)

**Communication Update** (after communication):
```cpp
τ_ij(t+1) = (1-ρ_comm) · τ_ij(t) + Δτ_ij
where Δτ_ij = Δτ_ij^1 + Δτ_ij^2 + Δτ_ij^3
```
- Three sources:
  - Δτ_ij^1: Local iteration-best
  - Δτ_ij^2: Received iteration-best (ring topology)
  - Δτ_ij^3: Received best-so-far (random topology)
- ρ_comm = 0.05 (much smaller than standard ρ)

**Contribution to Solving**:
- Parallel speedup: Multiple threads explore simultaneously
- Knowledge transfer: Good solutions spread across colonies
- Diversity: Different colonies explore different regions
- Robustness: Less likely to get stuck in local optima

---

### Algorithm 3: MultiThreadMultiColonyAntSystem (`multithreadmulticolonyantsystem.h`, `multithreadmulticolonyantsystem.cpp`)

**Purpose**: Multi-threaded system where each thread runs a MultiColonyAntSystem.

**Architecture**:
```
Thread 0: MultiColonyAntSystem (ACS colonies + MMAS colonies)
Thread 1: MultiColonyAntSystem (ACS colonies + MMAS colonies)
Thread 2: MultiColonyAntSystem (ACS colonies + MMAS colonies)
...
```

**Key Classes**:

#### `MultiColonyThread`
**Purpose**: Represents one thread running a MultiColonyAntSystem.

**Data Members**:
```cpp
int threadId;
MultiColonyAntSystem* multiColonySystem;  // The multi-colony system
Board iterationBest;                        // Best across all colonies this iteration
Board bestSol;                            // Best across all colonies ever
Board receivedIterationBest;              // From ring topology
Board receivedBestSol;                     // From random topology
```

**Key Methods**:
- `RunIteration()`: Runs one iteration of the multi-colony system
- `UpdatePheromoneWithCommunication()`: Updates MMAS colonies with three-source pheromone

**Contribution to Solving**:
- Combines benefits of multi-colony (ACS+MMAS) with multi-threading
- Each thread has multiple colonies with different behaviors
- Communication happens at thread level, not colony level

#### `MultiColonyAntSystem` (used within threads)
**Purpose**: Manages multiple colonies (ACS and MMAS types) within a single thread.

**Colony Types**:
- **ACS (type 0)**: Ant Colony System
  - Uses q0 parameter for exploitation
  - Standard pheromone update
- **MMAS (type 1)**: Max-Min Ant System
  - No q0 (pure exploration)
  - Pheromone clamped to [τ_min, τ_max]
  - Receives communication-based updates

**Key Features**:
- **Pheromone Fusion**: When ACS colonies have low entropy, merge with MMAS
- **Cooperative Game**: Allocate pheromone rewards based on performance
- **Public Path Recommendation**: Share best paths across colonies

**Contribution to Solving**:
- Hybrid approach: ACS for exploitation, MMAS for exploration
- Adaptive behavior: Switches between fusion and cooperation
- Knowledge sharing: Public path recommendation guides all colonies

---

## Friend Class Concept

### What is a Friend Class?

In C++, a **friend class** is a class that has been granted special access to another class's private and protected members. This is declared using the `friend` keyword.

**Syntax**:
```cpp
class Board {
    friend class CP;  // CP can access Board's private members
private:
    ValueSet *cells;
    int numUnits;
    // ...
};
```

### Why Use Friend Class Here?

#### The Problem

The `CP` module needs to:
1. Access `Board`'s private `cells` array to read and modify cell values
2. Access `Board`'s private `numUnits` to know puzzle size
3. Modify `Board`'s private `numInfeasible` counter
4. Call `Board::SetCell()` which may trigger recursive constraint propagation

#### Solution Options

**Option 1: Make Members Public** ❌
```cpp
class Board {
public:
    ValueSet *cells;  // Public - breaks encapsulation!
    int numUnits;
    // ...
};
```
**Problems**:
- Breaks encapsulation: Any code can modify internal state
- No control over how data is accessed
- Violates object-oriented principles
- Makes code harder to maintain

**Option 2: Public Getter/Setter Methods** ⚠️
```cpp
class Board {
public:
    ValueSet& GetCell(int i) { return cells[i]; }
    void SetCellValue(int i, const ValueSet& v) { cells[i] = v; }
    int GetNumUnits() { return numUnits; }
    void IncrementInfeasible() { numInfeasible++; }
    // ...
};
```
**Problems**:
- Verbose: Many methods needed
- Performance overhead: Function call overhead for frequent operations
- Still allows unrestricted access (anyone can call these)
- Doesn't express the special relationship between Board and CP

**Option 3: Friend Class** ✅ (Chosen)
```cpp
class Board {
    friend class CP;
private:
    ValueSet *cells;
    // ...
};
```
**Advantages**:
- **Encapsulation preserved**: Only CP can access private members
- **Performance**: Direct access, no function call overhead
- **Clear intent**: Explicitly declares special relationship
- **Controlled access**: Only one class has access, not everyone
- **Efficient**: Critical for constraint propagation (called very frequently)

### Why Friend Class is Appropriate Here

1. **Tight Coupling is Intentional**: CP and Board are designed to work together
   - CP is specifically for Board's constraint propagation
   - They form a cohesive unit

2. **Performance Critical**: Constraint propagation is called very frequently
   - Every cell setting triggers propagation
   - Direct access avoids function call overhead
   - In tight loops, this matters

3. **Controlled Access**: Only CP has access, not arbitrary code
   - Better than making everything public
   - Clear boundary: CP is the only external class with special access

4. **Design Pattern**: This is a valid use of friend classes
   - Common pattern: Helper classes that need internal access
   - Examples: Iterator classes, utility classes

### Alternative: Nested Class

Could we use a nested class instead?

```cpp
class Board {
private:
    class CP {
        static void ConstrainCell(Board& board, int i);
    };
    friend class CP;
};
```

**Pros**:
- Even tighter coupling
- CP is clearly part of Board's implementation

**Cons**:
- Less flexible: Harder to test CP independently
- Less modular: CP code mixed with Board code
- Current design (separate files) is cleaner

### Current Design Decision

The current design (separate CP class with friend access) is optimal because:
- **Modularity**: CP is in separate files, easier to maintain
- **Testability**: CP can be tested independently
- **Clarity**: Clear separation: Board = data, CP = algorithm
- **Performance**: Direct access when needed
- **Controlled**: Only CP has special access

---

## Data Flow

### Initial Puzzle Loading

```
solvermain.cpp
    ↓
Read puzzle string from file
    ↓
Board::Board(puzzleString)
    ↓
Parse string, initialize cells
    ↓
For each fixed cell:
    Board::SetCell()
        ↓
    CP::PropagateConstraints()
        ↓
    CP::ConstrainCell() for affected cells
        ↓
    Constraint propagation cascade
```

### Solving Process (Algorithm 2 Example)

```
MultiThreadSudokuAntSystem::Solve()
    ↓
Create N threads
    ↓
Each thread: SubColonyWorker()
    ↓
    SubColony::Initialize()
        - Create ants
        - Initialize pheromone matrix
    ↓
    Loop until solution found or timeout:
        SubColony::RunIteration()
            ↓
            For each ant:
                SudokuAnt::InitSolution()
                SudokuAnt::StepSolution() (repeated)
                    - Uses pheromone to choose values
                    - Calls Board::SetCell() → CP propagation
            ↓
            Find best ant solution
            ↓
            Update iterationBest
        ↓
        If communication interval:
            Barrier synchronization
            ↓
            CommunicateRingTopology()
            CommunicateRandomTopology()
            ↓
            SubColony::UpdatePheromoneWithCommunication()
        Else:
            SubColony::UpdatePheromone()
    ↓
Collect results from all threads
    ↓
Return best solution
```

### Constraint Propagation Flow

```
Ant sets a cell value
    ↓
Board::SetCell(cellIndex, value)
    ↓
cells[cellIndex] = value
numFixedCells++
    ↓
CP::PropagateConstraints(board, cellIndex)
    ↓
For each cell in same row/column/box:
    CP::ConstrainCell(board, affectedCell)
        ↓
        Calculate constraints from row/col/box
        ↓
        Eliminate impossible values
        ↓
        If only one possibility:
            Board::SetCell() (recursive!)
        ↓
        If cell becomes empty:
            numInfeasible++
```

---

## Design Decisions

### 1. Why Separate CP from Board?

**Decision**: Extract constraint propagation to separate CP module

**Reasoning**:
- **Single Responsibility**: Board handles data, CP handles algorithm
- **Maintainability**: Easier to modify constraint logic
- **Testability**: CP can be unit tested independently
- **Clarity**: Clear module boundaries

**Alternative Considered**: Keep everything in Board
- **Rejected**: Would mix data and algorithm, harder to maintain

### 2. Why Friend Class Instead of Public Methods?

**Decision**: Use friend class for CP to access Board's private members

**Reasoning**:
- **Performance**: Direct access in performance-critical code
- **Encapsulation**: Only CP has access, not everyone
- **Clarity**: Explicitly declares special relationship

**Alternatives Considered**:
- Public members: ❌ Breaks encapsulation
- Public getters/setters: ⚠️ Verbose, still too permissive
- Nested class: ⚠️ Less modular

### 3. Why Static Methods in CP?

**Decision**: CP methods are static

**Reasoning**:
- **No State**: CP doesn't maintain any state
- **Utility Class**: Pure functions, no instance needed
- **Simplicity**: Easier to use: `CP::ConstrainCell(board, i)`

**Alternative Considered**: Instance methods
- **Rejected**: Would require creating CP object, no benefit

### 4. Why Multi-Threading?

**Decision**: Use multiple threads for parallel exploration

**Reasoning**:
- **Speedup**: Multiple threads explore simultaneously
- **Diversity**: Different threads find different solutions
- **Robustness**: Less likely to get stuck

**Trade-offs**:
- **Complexity**: Requires synchronization
- **Overhead**: Thread creation and communication costs
- **Benefit**: Significant speedup for large puzzles

### 5. Why Two Communication Topologies?

**Decision**: Use both ring and random topologies

**Reasoning**:
- **Ring**: Deterministic, ensures all colonies get information
- **Random**: Provides diversity, different pairings each time
- **Complementary**: Ring for iteration-best (recent), random for best-so-far (historical)

**Alternative Considered**: Single topology
- **Rejected**: Less information diversity

### 6. Why Three-Source Pheromone Update?

**Decision**: Combine local + received iteration-best + received best-so-far

**Reasoning**:
- **Local**: Current colony's best work
- **Iteration-best**: Recent good solutions from neighbors
- **Best-so-far**: Historical best solutions
- **Balance**: Combines exploration and exploitation

**Alternative Considered**: Only local update
- **Rejected**: Misses benefits of communication

---

## Code File Reference

### Core Files

| File | Purpose | Key Contribution |
|------|---------|------------------|
| `valueset.h` | Bitmap-based set representation | Fast constraint checking |
| `board.h/cpp` | Puzzle state management | Foundation data structure |
| `CP.h/cpp` | Constraint propagation | Reduces search space |
| `timer.h` | High-resolution timing | Performance measurement |
| `sudokusolver.h` | Solver interface | Polymorphism support |

### Solver Files

| File | Purpose | Algorithm |
|------|---------|-----------|
| `sudokuantsystem.h/cpp` | Single-threaded ACS | Algorithm 0 |
| `sudokuant.h/cpp` | Individual ant | Solution construction |
| `backtracksearch.h/cpp` | Backtracking search | Algorithm 1 |
| `multithreadsudokuantsystem.h/cpp` | Multi-threaded ACS | Algorithm 2 |
| `multicolonyantsystem.h/cpp` | Multi-colony system | Used in Algorithm 3 |
| `colonyant.h/cpp` | Colony ant | Used in multi-colony |
| `multithreadmulticolonyantsystem.h/cpp` | Multi-thread multi-colony | Algorithm 3 |

### Utility Files

| File | Purpose |
|------|---------|
| `solvermain.cpp` | Entry point, argument parsing |
| `arguments.h` | Command-line argument parsing |
| `antcolonyinterface.h` | Interface for ant colonies |

---

## Summary

This Sudoku solver demonstrates:

1. **Modular Design**: Clear separation of concerns (Board, CP, Solvers)
2. **Advanced Algorithms**: Multiple ACO variants with communication
3. **Parallel Computing**: Multi-threaded execution with synchronization
4. **C++ Best Practices**: Friend classes, polymorphism, encapsulation
5. **Performance Optimization**: Bitmap sets, direct access via friend class

The **friend class** relationship between `Board` and `CP` is a carefully considered design decision that balances:
- **Encapsulation**: Private members remain protected
- **Performance**: Direct access for critical operations
- **Clarity**: Explicit declaration of special relationship
- **Maintainability**: Controlled access, not unrestricted

This design allows the constraint propagation algorithm to efficiently access Board's internal state while maintaining proper encapsulation and code organization.
