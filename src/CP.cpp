#include "CP.h"
#include "board.h"

// ============================================================================
// CONSTRAINT PROPAGATION MODULE
// ============================================================================
// This module contains all constraint propagation logic extracted from Board.
// Board delegates constraint propagation to this module.

// Initialize thread-local CP time pointer
thread_local float* CP::threadCPTime = nullptr;

void CP::RegisterThreadCPTime(float* cpTimePtr)
{
	threadCPTime = cpTimePtr;
}

void CP::UnregisterThreadCPTime()
{
	threadCPTime = nullptr;
}

void CP::AddTime(float elapsed)
{
	if (threadCPTime != nullptr)
		*threadCPTime += elapsed;
}

void CP::ConstrainCell(Board& board, int cellIndex)
{
	// Access Board's private members (friend class)
	if (board.cells[cellIndex].Empty() || board.cells[cellIndex].Fixed())
		return; // already set or empty
	
	int iBox, iCol, iRow;
	iBox = board.BoxForCell(cellIndex);
	iCol = board.ColForCell(cellIndex);
	iRow = board.RowForCell(cellIndex);

	// set of all fixed cells in row, column, box
	ValueSet colFixed(board.numUnits), rowFixed(board.numUnits), boxFixed(board.numUnits);
	// set of all open values in row, column, box, not including this cell
	ValueSet colAll(board.numUnits), rowAll(board.numUnits), boxAll(board.numUnits);

	for (int j = 0; j < board.numUnits; j++)
	{
		int k;
		k = board.BoxCell(iBox, j);
		if (k != cellIndex)
		{
			if (board.cells[k].Fixed())
				boxFixed += board.cells[k];
			boxAll += board.cells[k];
		}
		k = board.ColCell(iCol, j);
		if (k != cellIndex)
		{
			if (board.cells[k].Fixed())
				colFixed += board.cells[k];
			colAll += board.cells[k];
		}
		k = board.RowCell(iRow, j);
		if (k != cellIndex)
		{
			if (board.cells[k].Fixed())
				rowFixed += board.cells[k];
			rowAll += board.cells[k];
		}
	}
	ValueSet fixedCellsConstraint = ~(rowFixed + colFixed + boxFixed);

	if (fixedCellsConstraint.Fixed())
		SetCell(board, cellIndex, fixedCellsConstraint); // only one possibility left
	else
	{
		// eliminate all the values already taken in this cell's units
		board.cells[cellIndex] ^= fixedCellsConstraint;
		// are any of the remaining values for this cell in the only possible
		// place in a unit? If so, set the cell to that value
		if ((board.cells[cellIndex] - rowAll).Fixed())
			SetCell(board, cellIndex, board.cells[cellIndex] - rowAll);
		else if ((board.cells[cellIndex] - colAll).Fixed())
			SetCell(board, cellIndex, board.cells[cellIndex] - colAll);
		else if ((board.cells[cellIndex] - boxAll).Fixed())
			SetCell(board, cellIndex, board.cells[cellIndex] - boxAll);
	}
	if (board.cells[cellIndex].Empty())
		board.numInfeasible++;
}

void CP::SetCell(Board& board, int cellIndex, const ValueSet& value)
{
	// Check if cell is already fixed
	if (board.cells[cellIndex].Fixed())
		return; // already set
	
	// Set the cell
	board.cells[cellIndex] = value;
	board.numFixedCells++;
	
	// Propagate constraints using CP module
	PropagateConstraints(board, cellIndex);
}

void CP::PropagateConstraints(Board& board, int cellIndex)
{
	// Propagate constraints to all cells in the same row, column, and box
	int iBox, iCol, iRow;
	iBox = board.BoxForCell(cellIndex);
	iCol = board.ColForCell(cellIndex);
	iRow = board.RowForCell(cellIndex);

	for (int j = 0; j < board.numUnits; j++)
	{
		int k;
		k = board.BoxCell(iBox, j);
		if (k != cellIndex)
			ConstrainCell(board, k);
		k = board.ColCell(iCol, j);
		if (k != cellIndex)
			ConstrainCell(board, k);
		k = board.RowCell(iRow, j);
		if (k != cellIndex)
			ConstrainCell(board, k);
	}
}
