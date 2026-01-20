# CP Timing Implementation - Call Site Approach

## Overview
Time CP at each `SetCell` call site by:
1. Starting clock before `SetCell` call
2. Calculating elapsed time after call
3. Adding to thread's `cpTime` variable

## Implementation Steps

### Step 1: Add CPTime to Thread/Colony Classes

**MultiColonyThread** (Algorithm 3):
- Add `float cpTime;` member
- Add `float* GetCPTimePtr() { return &cpTime; }`
- Initialize `cpTime = 0.0f` in constructor

**SubColony** (Algorithm 2):
- Add `float cpTime;` member  
- Add `float* GetCPTimePtr() { return &cpTime; }`
- Initialize `cpTime = 0.0f` in constructor

### Step 2: Make CPTime Accessible to Ants

**Option A: Pass pointer through parent**
- Add `float* GetCPTimePtr()` method to `MultiColonyAntSystem`
- `MultiColonyAntSystem` gets pointer from `MultiColonyThread`
- `ColonyAnt` accesses via `parent->GetCPTimePtr()`

**Option B: Add to parent interface**
- Add `void AddCPTime(float elapsed)` method
- Parent accumulates to its CPTime

**Option C: Direct access through parent**
- `ColonyAnt` stores pointer: `float* cpTimePtr;`
- Set in constructor or initialization

### Step 3: Time at Call Sites

**colonyant.cpp** (2 call sites):
```cpp
// Before SetCell
auto startTime = std::chrono::steady_clock::now();
sol.SetCell(iCell, best);
auto endTime = std::chrono::steady_clock::now();
auto duration = std::chrono::duration_cast<std::chrono::duration<double>>(endTime - startTime);
float elapsed = (float)duration.count();
if (cpTimePtr != nullptr) *cpTimePtr += elapsed;
```

**sudokuant.cpp** (2 call sites):
- Same pattern

**backtracksearch.cpp** (1 call site):
- Need to handle (no thread context - could use global or skip)

**board.cpp constructor** (many calls during initialization):
- Could skip (initialization time) or use global counter

## Recommended: Option C (Direct Pointer)

### Changes Needed:

1. **colonyant.h**: Add `float* cpTimePtr;` member
2. **colonyant.cpp**: 
   - Set `cpTimePtr` in constructor or add setter
   - Time before/after `SetCell` calls
3. **multicolonyantsystem.h/cpp**: 
   - Add `float* cpTimePtr;` member
   - Add setter `void SetCPTimePtr(float* ptr)`
   - Pass to ants when creating them
4. **multithreadmulticolonyantsystem.cpp**:
   - Set `multiColonySystem->SetCPTimePtr(GetCPTimePtr())` in Initialize
5. **sudokuant.h/cpp**: Same pattern
6. **SubColony**: Same pattern

## Alternative: Simpler Approach

Instead of passing pointers, use a static method in CP:

```cpp
// CP.h
class CP {
    static thread_local float* threadCPTime;
public:
    static void RegisterThreadCPTime(float* ptr);
    static void UnregisterThreadCPTime();
    static void AddTime(float elapsed);
};

// At call site:
auto start = ...;
sol.SetCell(...);
auto end = ...;
CP::AddTime(elapsed);
```

This avoids passing pointers through the chain.
