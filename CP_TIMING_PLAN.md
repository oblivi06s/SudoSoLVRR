# CP Timing Implementation Plan

## Overview
Time constraint propagation (CP) work by measuring the duration of `SetCell` calls, which is the entry point for all CP operations.

## Design Principles

1. **Entry Point Timing**: Time at `CP::SetCell()` - this is the single entry point that triggers all CP work
2. **Avoid Double-Counting**: Only time top-level `SetCell` calls (not recursive calls from `ConstrainCell`)
3. **Per-Thread Support**: Support per-thread timing for multi-threaded algorithms
4. **Simple & Clean**: Use a straightforward clock-based approach

## Call Flow Analysis

```
External Code (ant, backtrack, etc.)
  └─> Board::SetCell()
       └─> CP::SetCell()  [TIME HERE - Entry Point]
            └─> CP::PropagateConstraints()
                 └─> CP::ConstrainCell() [multiple times]
                      └─> CP::SetCell() [RECURSIVE - Don't time]
                           └─> ... (recursive chain)
```

## Implementation Strategy

### Option 1: Time at CP::SetCell with Recursion Detection (Recommended)

**Approach**: 
- Add a `thread_local bool` flag to detect if we're already inside a `SetCell` call
- Only time when the flag is `false` (top-level call)
- Set flag to `true` at start, `false` at end

**Pros**:
- Clean separation - timing logic stays in CP module
- Automatically handles all entry points
- No changes needed to external code

**Cons**:
- Requires thread-local storage

### Option 2: Time at Board::SetCell

**Approach**:
- Time in `Board::SetCell()` before calling `CP::SetCell()`
- This naturally only times top-level calls

**Pros**:
- Even simpler - no recursion detection needed
- All external calls go through `Board::SetCell()`

**Cons**:
- Timing logic in Board instead of CP module
- Less modular

### Option 3: Time at External Call Sites

**Approach**:
- Time before/after each `Board::SetCell()` call in external code

**Pros**:
- Explicit control at call sites

**Cons**:
- Requires changes in many places (ants, backtrack, etc.)
- Easy to miss some calls
- Not clean or maintainable

## Recommended Implementation: Option 1

### Structure

```cpp
// CP.h
class CP {
private:
    static thread_local bool insideSetCell;  // Track recursive calls
    static thread_local float* threadCPTime; // Per-thread CP time accumulator
    
public:
    // Register thread's CP time pointer (for multi-threaded algorithms)
    static void RegisterThreadCPTime(float* cpTimePtr);
    static void UnregisterThreadCPTime();
    
    static void SetCell(Board& board, int cellIndex, const ValueSet& value);
    // ... other methods
};
```

### Timing Logic in CP::SetCell()

```cpp
void CP::SetCell(Board& board, int cellIndex, const ValueSet& value)
{
    // Check if this is a top-level call (not recursive)
    bool isTopLevel = !insideSetCell;
    auto startTime = std::chrono::steady_clock::now();
    
    // Mark that we're inside a SetCell call
    insideSetCell = true;
    
    // ... existing SetCell logic ...
    
    // Reset flag
    insideSetCell = false;
    
    // Only accumulate time for top-level calls
    if (isTopLevel) {
        auto endTime = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::duration<double>>(
            endTime - startTime);
        float elapsed = (float)duration.count();
        
        // Update per-thread CP time if registered
        if (threadCPTime != nullptr)
            *threadCPTime += elapsed;
    }
}
```

## Per-Thread Timing Support

For multi-threaded algorithms (Algorithm 2 & 3):

1. Each thread/colony has a `float cpTime` member variable
2. At thread start: `CP::RegisterThreadCPTime(&thread->cpTime)`
3. At thread end: `CP::UnregisterThreadCPTime()`
4. CP automatically accumulates time into the registered pointer

## Global Statistics (Optional)

If we want global CP statistics:
- Add a static `CPStats` structure
- Use mutex for thread-safe updates
- Provide `GetStats()` and `ResetStats()` methods

## Benefits of This Approach

1. ✅ **Clean**: Timing logic centralized in CP module
2. ✅ **Automatic**: No changes needed to external code
3. ✅ **Accurate**: Only times actual CP work, no double-counting
4. ✅ **Flexible**: Supports both per-thread and global timing
5. ✅ **Simple**: Straightforward clock-based timing

## Example Usage

```cpp
// In multi-threaded algorithm:
void ThreadWorker() {
    float cpTime = 0.0f;
    CP::RegisterThreadCPTime(&cpTime);
    
    // ... solve puzzle ...
    // All CP::SetCell() calls automatically accumulate to cpTime
    
    CP::UnregisterThreadCPTime();
    // Now cpTime contains total CP time for this thread
}
```
