#pragma once
#include "valueset.h"
#include <string>
#include <vector>
using namespace std;

// Forward declaration
class CP;

class Board
{
	friend class CP;  // Allow CP to access private members for constraint propagation
public:
	// sudoku board
	Board(){};
	Board(const string &puzzleString);
	Board(const Board &other);
	~Board();

	string AsString(bool useNmbers=false, bool showUnfixed = false);
	int FixedCellCount(void) const;
	int InfeasibleCellCount(void) const;
	void SetCell(int i, const ValueSet &c );
	const ValueSet &GetCell(int i) const;

	int GetNumUnits() const;
	void Copy(const Board &other);
	int CellCount(void) const;
	bool CheckSolution(const Board& other) const;
	// helpers
	int RowCell(int iRow, int iCell) const;
	int ColCell(int iCol, int iCell) const;
	int BoxCell(int iBox, int iCell) const;
	int RowForCell(int iCell) const;
	int ColForCell(int iCell) const;
	int BoxForCell(int iCell) const;


private:
	ValueSet *cells = nullptr;

	int order;   // order of puzzle (for square grids only, 0 for rectangular)
	int boxRows; // height of each box (e.g., 2 for 6x6, 3 for 9x9, 3 for 12x12)
	int boxCols; // width of each box (e.g., 3 for 6x6, 3 for 9x9, 4 for 12x12)
	int numUnits; // number of units (rows, columns, blocks)
	int numCells; // numer of cells
	int numFixedCells; // number of cells with uniquely determined value
	int numInfeasible; // number of cells with no possibilities.
	void Eliminate(int i, const ValueSet &c );
	void Eliminate2(int i, const ValueSet &c );
	// ConstrainCell moved to CP module
};