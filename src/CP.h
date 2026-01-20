#pragma once
#include "valueset.h"

// Forward declaration
class Board;

// Constraint Propagation module
// Handles all constraint propagation logic for Sudoku boards
class CP
{
private:
	// Thread-local pointer to current thread's CP time accumulator
	// Each thread registers its CPTime variable pointer here
	static thread_local float* threadCPTime;
	
public:
	// Register thread's CP time pointer (call at thread initialization)
	// The pointer will be used to accumulate CP time for that thread
	static void RegisterThreadCPTime(float* cpTimePtr);
	
	// Unregister thread's CP time pointer (call at thread cleanup)
	static void UnregisterThreadCPTime();
	
	// Add elapsed time to the registered thread's CP time accumulator
	// Call this after timing a SetCell operation
	static void AddTime(float elapsed);
	
	// Constrain a single cell based on its row, column, and box constraints
	// This is the core constraint propagation algorithm
	static void ConstrainCell(Board& board, int cellIndex);
	
	// Set a cell and propagate constraints
	// This is the entry point for setting cells - it handles the cell assignment
	// and triggers constraint propagation
	static void SetCell(Board& board, int cellIndex, const ValueSet& value);
	
	// Propagate constraints after setting a cell
	// Calls ConstrainCell for all affected cells in the same row, column, and box
	static void PropagateConstraints(Board& board, int cellIndex);
};
