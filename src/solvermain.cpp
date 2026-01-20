#include "sudokuantsystem.h"
#include "multithreadsudokuantsystem.h"
#include "multithreadmulticolonyantsystem.h"
#include "sudokusolver.h"
#include "backtracksearch.h"
#include "board.h"
#include "arguments.h"
#include <iostream>
#include <fstream>
#include <string>
#include <iomanip>
using namespace std;

string ReadFile( string fileName )
{
	char *puzString;
	ifstream inFile;
	inFile.open(fileName);
	if ( inFile.is_open() )
	{
		int firstNumber, idum;
		inFile >> firstNumber;
		inFile >> idum;
		
		// Read all values into a vector first
		vector<int> values;
		int val;
		while (inFile >> val)
		{
			values.push_back(val);
		}
		inFile.close();
		
		// Determine format based on number of values
		int numUnits;
		bool isOldFormat = false;
		
		// Old format: firstNumber is order, has order^4 values
		// New format: firstNumber is size, has size^2 values
		if (values.size() == firstNumber * firstNumber * firstNumber * firstNumber)
		{
			// Old format (9x9, 16x16, 25x25): firstNumber is order
			isOldFormat = true;
			numUnits = firstNumber * firstNumber;
		}
		else if (values.size() == firstNumber * firstNumber)
		{
			// New format (6x6, 12x12): firstNumber is size
			isOldFormat = false;
			numUnits = firstNumber;
		}
		else
		{
			cerr << "Invalid file format: expected " << firstNumber * firstNumber 
			     << " or " << firstNumber * firstNumber * firstNumber * firstNumber 
			     << " values, got " << values.size() << endl;
			return string();
		}
		
		int numCells = numUnits * numUnits;
		puzString = new char[numCells+1];
		
		for (int i = 0; i < numCells; i++)
		{
			val = values[i];
			if (val == -1)
				puzString[i] = '.';
			else if (numUnits == 6)
				puzString[i] = '1' + (val - 1);  // 1-6 -> '1'-'6'
			else if (numUnits == 9)
				puzString[i] = '1' + (val - 1);  // 1-9 -> '1'-'9'
			else if (numUnits == 12)
			{
				if (val <= 10)
					puzString[i] = '0' + val - 1;  // 1-10 -> '0'-'9'
				else
					puzString[i] = 'a' + val - 11;  // 11-12 -> 'a'-'b'
			}
			else if (numUnits == 16)
			{
				if (val < 11)
					puzString[i] = '0' + val - 1;
				else
					puzString[i] = 'a' + val - 11;
			}
			else  // 25x25 and larger
				puzString[i] = 'a' + val - 1;
		}
		puzString[numCells] = 0;
		string retVal = string(puzString);
		delete [] puzString;
		return retVal;
	}
	else
	{
		cerr << "could not open file: " << fileName << endl;
		return string();
	}
}

int main( int argc, char *argv[] )
{
	// solve, then spit out 0 for success, 1 for fail, followed by time in seconds
	Arguments a( argc, argv );
	string puzzleString;
	if ( a.GetArg("blank", 0 ) && a.GetArg("order", 0 ))
	{
		int order = a.GetArg("order", 0 );
		if ( order != 0 )
			puzzleString = string(order*order*order*order,'.');
	}
	else 
	{
		// read in the puzzle from a one-line string
		puzzleString = a.GetArg(string("puzzle"),string());
		if ( puzzleString.length() == 0 )
		{
			// try from a file
			string fileName = a.GetArg(string("file"),string());
			puzzleString = ReadFile(fileName);
		}
		if ( puzzleString.length() == 0 )
		{
			cerr << "no puzzle specified" << endl;
			exit(0);
		}
	}
	Board board(puzzleString);

	int algorithm = a.GetArg("alg", 0);
	int timeOutSecs = a.GetArg("timeout", 120);
	int nAnts = a.GetArg("ants", 4);  // Default: 3 ants per colony (for alg 3: 3 colonies × 3 ants = 9 ants per thread)
	int nSubColonies = a.GetArg("subcolonies", 4);
	int nThreads = a.GetArg("threads", 3);  // For algorithm 3 (MultiThreadMultiColonyAntSystem)
	int numACS = a.GetArg("numacs", 3);  // For algorithm 3: number of ACS colonies per thread
	int numColonies = a.GetArg("numcolonies", numACS+1);  // For algorithm 3: total colonies per thread (default: 3)
	float q0 = a.GetArg("q0", 0.9f);
	float rho = a.GetArg("rho", 0.9f);  // Standard ACS rho (used in Alg 0 and internally in Alg 2)
	float rhoComm = a.GetArg("rhocomm", 0.9f);  // Communication evaporation rate (Alg 2 only)
	float evap = a.GetArg("evap", 0.005f );
	float convThreshold = a.GetArg("convthreshold", 0.8f);  // For algorithm 3: MMAS convergence threshold
	float entropyThreshold = a.GetArg("entropythreshold", 2.0f);  // For algorithm 3: entropy threshold
	bool blank = a.GetArg("blank", false );
	bool verbose = a.GetArg("verbose", 0);
	bool showInitial = a.GetArg("showinitial", 0);
	bool success;

	float solTime;
	Board solution;
	SudokuSolver *solver;
	
	if ( algorithm == 0 )
		solver = new SudokuAntSystem( nAnts, q0, rho, 1.0f/board.CellCount(), evap);
	else if ( algorithm == 1 )
		solver = new BacktrackSearch();
	else if ( algorithm == 2 )
		solver = new MultiThreadSudokuAntSystem( nSubColonies, nAnts, q0, rho, rhoComm, 1.0f/board.CellCount(), evap);
	else if ( algorithm == 3 )
		solver = new MultiThreadMultiColonyAntSystem( nThreads, nAnts, q0, rho, 1.0f/board.CellCount(), evap,
		                                               numColonies, numACS, convThreshold, entropyThreshold);
	else
		solver = new BacktrackSearch();

	
	if ( showInitial )
	{
		// print inital grid
		cout << "Initial constrained grid" << endl;
		cout << board.AsString(false,true) << endl;
	}
	
	success = solver->Solve(board, (float)timeOutSecs );
	solution = solver->GetSolution();
	solTime = solver->GetSolutionTime();

	// sanity chack the solution:
	if ( success && !board.CheckSolution(solution) )
	{
		cout << "solution not valid" << a.GetArg("file",string()) << " " << algorithm << endl;
		cout << "numfixedCells " << solution.FixedCellCount() << endl;

		string outString = solution.AsString(true );
		cout << outString << endl;

		success = false;
	}
	
	if ( !verbose )
		cout << !success << endl << solTime << endl;
	else
	{
		if ( !success )
		{
			cout << "failed in time " << solTime << endl;
			// Show iterations for algorithm 2
			if ( algorithm == 2 )
			{
				MultiThreadSudokuAntSystem* parallelSolver = dynamic_cast<MultiThreadSudokuAntSystem*>(solver);
				if ( parallelSolver )
				{
					cout << "iterations: " << parallelSolver->GetIterationsCompleted() << endl;
					cout << "communication: " << (parallelSolver->GetCommunicationOccurred() ? "yes" : "no") << endl;
					if ( verbose )
						parallelSolver->PrintColonyDetails();
				}
			}
			// Show iterations for algorithm 3
			else if ( algorithm == 3 )
			{
				MultiThreadMultiColonyAntSystem* multiThreadSolver = dynamic_cast<MultiThreadMultiColonyAntSystem*>(solver);
				if ( multiThreadSolver )
				{
					cout << "iterations: " << multiThreadSolver->GetIterationsCompleted() << endl;
					cout << "communication: " << (multiThreadSolver->GetCommunicationOccurred() ? "yes" : "no") << endl;
					if ( verbose )
						multiThreadSolver->PrintThreadDetails();
				}
			}
		}
		else
		{
			cout << "Solution:" << endl;
			string outString = solution.AsString( true );
			cout << outString << endl;
			cout << "solved in " << solTime << endl;
			if(algorithm ==0){
				SudokuAntSystem* sudokuSolver = dynamic_cast<SudokuAntSystem*>(solver);
				if ( sudokuSolver )
				{
					sudokuSolver->PrintCPTime();
				}
			}
			// Show iterations for algorithm 2
			if ( algorithm == 2 )
			{
				MultiThreadSudokuAntSystem* parallelSolver = dynamic_cast<MultiThreadSudokuAntSystem*>(solver);
				if ( parallelSolver )
				{
					cout << "iterations: " << parallelSolver->GetIterationsCompleted() << endl;
					cout << "communication: " << (parallelSolver->GetCommunicationOccurred() ? "yes" : "no") << endl;
					if ( verbose )
						parallelSolver->PrintColonyDetails();
				}
			}
			// Show iterations for algorithm 3
			else if ( algorithm == 3 )
			{
				MultiThreadMultiColonyAntSystem* multiThreadSolver = dynamic_cast<MultiThreadMultiColonyAntSystem*>(solver);
				if ( multiThreadSolver )
				{
					cout << "iterations: " << multiThreadSolver->GetIterationsCompleted() << endl;
					cout << "communication: " << (multiThreadSolver->GetCommunicationOccurred() ? "yes" : "no") << endl;
					if ( verbose )
						multiThreadSolver->PrintThreadDetails();
				}
			}
		}
	}
}
