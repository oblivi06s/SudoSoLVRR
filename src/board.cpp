#include "board.h"
#include "CP.h"
#include <iostream>
#include <iomanip>
#include <inttypes.h>
#include <string>
#include <sstream>
//
// description of a sudoku board, with functions for setting cells and propagating constraints
//
Board::Board(const string &puzzleString)
{
	// check this is a supported puzzle size
	switch (puzzleString.length())
	{
	case 36:    // 6x6
		order = 0;  // Not a square grid
		boxRows = 2;
		boxCols = 3;
		numUnits = 6;
		break;
	case 81:    // 9x9
		order = 3;
		boxRows = 3;
		boxCols = 3;
		numUnits = 9;
		break;
	case 144:   // 12x12
		order = 0;  // Not a square grid
		boxRows = 3;
		boxCols = 4;
		numUnits = 12;
		break;
	case 256:   // 16x16
		order = 4;
		boxRows = 4;
		boxCols = 4;
		numUnits = 16;
		break;
	case 625:   // 25x25
		order = 5;
		boxRows = 5;
		boxCols = 5;
		numUnits = 25;
		break;
	case 1296:  // 36x36
		order = 6;
		boxRows = 6;
		boxCols = 6;
		numUnits = 36;
		break;
	case 2401:  // 49x49
		order = 7;
		boxRows = 7;
		boxCols = 7;
		numUnits = 49;
		break;
	case 4096:  // 64x64
		order = 8;
		boxRows = 8;
		boxCols = 8;
		numUnits = 64;
		break;
	default:
		std::cerr << "wrong number of cells for a sudoku board!" << std::endl;
		order = 0;
		boxRows = 0;
		boxCols = 0;
		numUnits = 0;
		break;
	}

	numCells = numUnits * numUnits;
	
	cells = new ValueSet[numCells];

	int maxVal = numUnits;

	for (int i = 0; i < numCells; i++)
		cells[i].Init(maxVal);

	// set all possibilities for all cells
	for ( int i = 0; i < numCells; i++ )
	{
		cells[i] = ~cells[i];
	}
	// set the known cells one by one
	numInfeasible = 0;
	numFixedCells = 0;
	for (int i = 0; i < numCells; i++)
	{
		if (puzzleString[i] != '.')
		{
			int value;
			if (numUnits == 6)
			{
				// 6x6: use '1'-'6'
				value = (int)(puzzleString[i] - '0');
			}
			else if (numUnits == 9)
			{
				// 9x9: use '1'-'9'
				value = (int)(puzzleString[i] - '0');
			}
			else if (numUnits == 12)
			{
				// 12x12: use '0'-'9' then 'a'-'b'
				if (puzzleString[i] >= '0' && puzzleString[i] <= '9')
					value = 1 + (int)(puzzleString[i] - '0');
				else
					value = 11 + (int)(puzzleString[i] - 'a');
			}
			else if (numUnits == 16)
			{
				// 16x16: use '0'-'9' then 'a'-'f'
				if (puzzleString[i] >= '0' && puzzleString[i] <= '9')
					value = 1 + (int)(puzzleString[i] - '0');
				else
					value = 11 + (int)(puzzleString[i] - 'a');
			}
			else
			{
				// 25x25 and larger: use 'a'-'y', etc.
				value = 1 + (int)(puzzleString[i] - 'a');
			}
			SetCell( i, ValueSet(maxVal, (int64_t)1 << (value-1) ));
		}
	}
}

Board::Board(const Board &other)
{
	Copy(other);
}

void Board::Copy(const Board& other)
{
	order = other.order;
	boxRows = other.boxRows;
	boxCols = other.boxCols;
	numUnits = other.numUnits;
	numCells = numUnits * numUnits;

	if (cells == nullptr)
		cells = new ValueSet[numCells];

	int maxVal = numUnits;

	for (int i = 0; i < numCells; i++)
		cells[i] = other.GetCell(i);

	numFixedCells = other.FixedCellCount();
	numInfeasible = other.InfeasibleCellCount();
}

Board::~Board()
{
	if ( cells != nullptr ) delete [] cells;
}

int Board::RowCell(int iRow, int iCell) const
{
	// returns cell index of the iCell'th cell in the iRow'th row
	return iRow * numUnits + iCell;
}

int Board::ColCell(int iCol, int iCell) const
{
	// returns cell index of the iCell'th cell in the iCol'th column
	return iCell * numUnits + iCol;
}

int Board::BoxCell(int iBox, int iCell) const
{
	// returns cell index of the iCell'th cell in the iBox'th box
	// Number of boxes per row = numUnits / boxCols
	int boxesPerRow = numUnits / boxCols;
	int boxCol = iBox % boxesPerRow;     // Which box column (0 to boxesPerRow-1)
	int boxRow = iBox / boxesPerRow;     // Which box row (0 to boxesPerRow-1)
	
	// Top-left corner of this box in grid coordinates
	int topCorner = (boxCol * boxCols) + (boxRow * boxRows * numUnits);
	
	// Cell position within the box
	int cellCol = iCell % boxCols;
	int cellRow = iCell / boxCols;
	
	return topCorner + cellCol + (cellRow * numUnits);
}

int Board::RowForCell(int iCell) const
{
	// returns index of the row which contains cell iCell 
	return iCell / numUnits;
}

int Board::ColForCell(int iCell) const
{
	// returns index of the column which contains cell iCell 
	return iCell % numUnits;
}

int Board::BoxForCell(int iCell) const
{
	// returns index of the box which contains cell iCell
	int cellRow = iCell / numUnits;
	int cellCol = iCell % numUnits;
	
	int boxRow = cellRow / boxRows;
	int boxCol = cellCol / boxCols;
	
	int boxesPerRow = numUnits / boxCols;
	return boxRow * boxesPerRow + boxCol;
}

string Board::AsString(bool useNumbers, bool showUnfixed )
{
	/*
	  Form a human-readable string from the board, using either numbers (1..numUnits) or a single character
	  per cell (9x9 - 1-9, 16x16 0-f, 25x25 - a-y). If showUnfixed is true, show the possibilies in
	  an unfixed cell (otherwise represent it is as '.'). If order is 4 or 5 and showUnfixed is true, force useNumbers to 
	  false for readability.
	 */

	if ( showUnfixed )
		useNumbers = false;

	stringstream puzString;
	string alphabet;

	if ( !useNumbers )
	{
		if ( numUnits == 6 )
			alphabet = string("123456");
		else if ( numUnits == 9 )
			alphabet = string("123456789");
		else if ( numUnits == 12 )
			alphabet = string("0123456789ab");
		else if ( numUnits == 16 )
			alphabet = string("0123456789abcdef");
		else
			alphabet = string("abcdefghijklmnopqrstuvwxy");
	}

	vector<string> cellStrings;
	size_t maxLen = 0;
	for (int i = 0; i < numCells; i++)
	{
		string cellContents;
		if ( !useNumbers )
		{
			if ( !showUnfixed && !cells[i].Fixed())
				cellContents = string(".");
			else
				cellContents = cells[i].toString(alphabet);
		}
		else 
			cellContents = to_string(cells[i].Index() + 1);
		if (cellContents.size() > maxLen )
			maxLen = cellContents.size();
		cellStrings.push_back(cellContents);
	}
	int pitch = static_cast<int>(maxLen + 1); 
	for ( int i = 0; i < numCells; i++ )
	{
		puzString << setw(pitch) << cellStrings[i] << " ";
		if ( i%numUnits == numUnits -1 )
		{
			if ( i != numCells-1 )
				puzString << endl;
		}
		else if (i%boxCols == boxCols-1 )
			puzString << string("|");
		if ( i%(numUnits*boxRows) == numUnits*boxRows-1 && i != numCells-1)
		{
			int boxesPerRow = numUnits / boxCols;
			for ( int j = 0; j < boxesPerRow; j++ )
			{
				for ( int k = 0; k < boxCols*(pitch+1); k++ )
					puzString << '-';
				if ( j != boxesPerRow-1 )
					puzString << '+';
			}
			puzString << endl;
		}
	}
	return puzString.str();
}

void Board::SetCell(int i, const ValueSet &c )
{
	// Delegate to CP module - all constraint propagation logic is in CP
	CP::SetCell(*this, i, c);
}

const ValueSet& Board::GetCell(int i) const
{
	return cells[i];
}

int Board::FixedCellCount(void) const
{
	return numFixedCells;
}

int Board::InfeasibleCellCount(void) const
{
	return numInfeasible;
}

int Board::CellCount(void) const
{
	return numCells;
}

int Board::GetNumUnits(void) const
{
	return numUnits;
}

bool Board::CheckSolution(const Board& other) const
{
	// check that other is 1/ a solution, 2/ consistent with this board
	if (other.CellCount() != CellCount())
		return false;
	bool isSolution = true;
	bool isConsistent = true;

	// check its a solution
	// first - all cells must be filled
	for (int i = 0; i < other.CellCount(); i++)
	{
		if (!other.GetCell(i).Fixed())
			isSolution = false;
	}
	// second - all rows, columns, boxes must have one of each number
	for (int i = 0; i < numUnits; i++)
	{
		ValueSet row, col, box;
		row.Init(numUnits);
		col.Init(numUnits);
		box.Init(numUnits);
		for (int j = 0; j < numUnits; j++)
		{
			row += other.GetCell(RowCell(i, j));
			col += other.GetCell(ColCell(i, j));
			box += other.GetCell(BoxCell(i, j));
		}
		if (row.Count() != numUnits || col.Count() != numUnits || box.Count() != numUnits )
			isSolution = false;
	}

	// check consistency with this board
	for (int i = 0; i < CellCount(); i++)
	{
		if (GetCell(i).Fixed())
		{
			if (GetCell(i).Index() != other.GetCell(i).Index() )
				isConsistent = false;
		}
	}

	return isSolution && isConsistent;
}