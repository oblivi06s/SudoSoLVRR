/*******************************************************************************
 * SUDOKU SOLVER - Main Entry Point
 * 
 * This is the main executable for the Sudoku solver. It provides a
 * command-line interface for running different solving algorithms.
 * 
 * Execution Flow:
 * 1. Read puzzle from file or command line
 * 2. Initialize board (triggers constraint propagation)
 * 3. Select and configure algorithm
 * 4. Run solver
 * 5. Validate and output results
 * 
 * Supported Algorithms:
 * - Algorithm 0: Single-threaded Ant Colony System (ACS)
 * - Algorithm 1: Backtracking search
 * - Algorithm 2: Parallel ACS with multiple sub-colonies
 ******************************************************************************/

#include "sudokuantsystem.h"
#include "parallelsudokuantsystem.h"
#include "multicolonyantsystem.h"
#include "multithreadmulticolonyantsystem.h"
#include "backtracksearch.h"
#include "sudokusolver.h"
#include "board.h"
#include "arguments.h"
#include "constraintpropagation.h"
#include <iostream>
#include <fstream>
#include <string>
#include <iomanip>
#include <sstream>
using namespace std;

static string JsonEscape(const string &input)
{
	ostringstream out;
	for (char c : input)
	{
		switch (c)
		{
		case '\\': out << "\\\\"; break;
		case '"': out << "\\\""; break;
		case '\n': out << "\\n"; break;
		case '\r': out << "\\r"; break;
		case '\t': out << "\\t"; break;
		default: out << c; break;
		}
	}
	return out.str();
}

// ============================================================================
// SECTION 1: PUZZLE FILE READER
// ============================================================================

/*******************************************************************************
 * ReadFile - Read a Sudoku puzzle from a text file
 * 
 * File format:
 *   Line 1: order (e.g., 3 for 9x9, 4 for 16x16, 5 for 25x25)
 *   Line 2: ignored value
 *   Remaining: cell values (one per line)
 *     -1 represents empty cell (.)
 *     1-9 (for 9x9), 1-16 (for 16x16), etc. represent fixed values
 * 
 * Parameters:
 *   fileName - Path to the puzzle file
 * 
 * Returns: Puzzle string representation (e.g., "4.5...2.1...")
 ******************************************************************************/
string ReadFile( string fileName )
{
	char *puzString;
	ifstream inFile;
	inFile.open(fileName);
	if ( inFile.is_open() )
	{
		int order, idum;
		inFile >> order;
		int numCells = order*order*order*order;
		inFile >> idum;
		puzString = new char[numCells+1];
		for (int i = 0; i < numCells; i++)
		{
			int val;
			inFile >> val;
			if (val == -1)
				puzString[i] = '.';
			else if (order == 3)
				puzString[i] = '1' + (val - 1);
			else if (order == 4)
				if (val < 11)
					puzString[i] = '0' + val - 1;
				else
					puzString[i] = 'a' + val - 11;
			else
				puzString[i] = 'a' + val - 1;
		}
		puzString[numCells] = 0;
		inFile.close();
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

// ============================================================================
// SECTION 2: MAIN FUNCTION
// ============================================================================

/*******************************************************************************
 * main - Entry point for the Sudoku solver
 * 
 * This function orchestrates the entire solving process:
 * 1. Parse command-line arguments
 * 2. Load puzzle
 * 3. Initialize board (applies constraint propagation)
 * 4. Configure and run selected algorithm
 * 5. Validate and output results
 ******************************************************************************/
int main( int argc, char *argv[] )
{
	// ========================================================================
	// SECTION 2.1: COMMAND-LINE ARGUMENT PARSING
	// ========================================================================
	
	Arguments a( argc, argv );
	string puzzleString;
	
	// Option 1: Generate blank puzzle of specified order
	if ( a.GetArg("blank", 0) && a.GetArg("order", 0))
	{
		int order = a.GetArg("order", 0);
		if ( order != 0 )
			puzzleString = string(order*order*order*order,'.');
	}
	// Option 2: Read puzzle from command line or file
	else 
	{
		// Try reading from command-line argument
		puzzleString = a.GetArg(string("puzzle"),string());
		if ( puzzleString.length() == 0 )
		{
			// Try reading from file
			string fileName = a.GetArg(string("file"),string());
			puzzleString = ReadFile(fileName);
		}
		if ( puzzleString.length() == 0 )
		{
			cerr << "no puzzle specified" << endl;
			exit(0);
		}
	}
	
	// Reset CP timing before starting
	ResetCPTiming();
	
	// Initialize board (triggers constraint propagation)
	Board board(puzzleString);

	// Parse algorithm parameters
	int algorithm = a.GetArg("alg", 0);
	int timeOutSecs = a.GetArg("timeout", -1);
	int nAnts = a.GetArg("ants", 10);
	int nThreads = a.GetArg("threads", 4);
	float q0 = a.GetArg("q0", 0.9f);
	float rho = a.GetArg("rho", 0.9f);  
	float evap = a.GetArg("evap", 0.005f);
	
	// Parameters for algorithms 3 and 4 (multi-colony)
	int numACS = a.GetArg("numacs", 3);
	int numColonies = a.GetArg("numcolonies", numACS + 1);
	float convThreshold = a.GetArg("convthreshold", 0.08f);
	float entropyThreshold = a.GetArg("entropythreshold", 5.0f);
	
	bool blank = a.GetArg("blank", false);
	bool verbose = a.GetArg("verbose", 0);
	bool showInitial = a.GetArg("showinitial", 0);
	bool jsonOutput = a.GetArg("json", 0);
	bool success;

	if ( timeOutSecs <= 0 )
	{
		int cellCount = board.CellCount();
		if ( cellCount == 81 )
			timeOutSecs = 5;
		else if ( cellCount == 256 )
			timeOutSecs = 20;
		else if ( cellCount == 625 )
			timeOutSecs = 120;
		else
			timeOutSecs = 120;
	}

	float solTime;
	Board solution;
	SudokuSolver *solver;
	
	// ========================================================================
	// SECTION 2.2: ALGORITHM SELECTION & CONFIGURATION
	// ========================================================================
	
	if ( algorithm == 0 )
		solver = new SudokuAntSystem( nAnts, q0, rho, 1.0f/board.CellCount(), evap);
	else if ( algorithm == 1 )
		solver = new BacktrackSearch();
	else if ( algorithm == 2 )
		solver = new ParallelSudokuAntSystem( nThreads, nAnts, q0, rho, 1.0f/board.CellCount(), evap);
	else if ( algorithm == 3 )
		solver = new MultiColonyAntSystem( nAnts, q0, rho, 1.0f/board.CellCount(), evap, numColonies, numACS, convThreshold, entropyThreshold);
	else if ( algorithm == 4 )
		solver = new MultiThreadMultiColonyAntSystem( nThreads, nAnts, q0, rho, 1.0f/board.CellCount(), evap, numColonies, numACS, convThreshold, entropyThreshold);
	else
	{
		cerr << "Invalid algorithm: " << algorithm << ". Use 0 (single-thread ACS), 1 (backtracking), 2 (parallel ACS), 3 (multi-colony), or 4 (multi-thread multi-colony)." << endl;
		exit(1);
	}

	// Optionally show the puzzle after constraint propagation
	if ( showInitial )
	{
		cout << "Initial constrained grid" << endl;
		cout << board.AsString(false, true) << endl;
	}
	
	// ========================================================================
	// SECTION 2.3: RUN SOLVER
	// ========================================================================
	
	success = solver->Solve(board, (float)timeOutSecs);
	solution = solver->GetSolution();
	solTime = solver->GetSolutionTime();
	

	// ========================================================================
	// SECTION 2.4: SOLUTION VALIDATION & OUTPUT
	// ========================================================================
	
	// Sanity check the solution
	string errorMessage;
	if ( success && !board.CheckSolution(solution) )
	{
		errorMessage = "solution not valid";
		if ( !jsonOutput )
		{
			cout << "solution not valid" << a.GetArg("file",string()) << " " << algorithm << endl;
			cout << "numfixedCells " << solution.FixedCellCount() << endl;

			string outString = solution.AsString(true );
			cout << outString << endl;
		}
		success = false;
	}
	
	// Get CP timing statistics
	float initialCPTime = GetInitialCPTime();
	solTime = solTime + initialCPTime;
	
	float antCPTime = GetAntCPTime();
	int cpCallCount = GetCPCallCount();
	
	// Timing values from winning thread (for multi-threaded algorithms)
	float winningThreadCPTime = antCPTime;  // Default to global for single-threaded
	float winningThreadAntGuessingTime = 0.0f;  // Default to 0, will be set below
	float coopGameTime = 0.0f;
	float pheromoneFusionTime = 0.0f;
	float publicPathTime = 0.0f;
	float winningThreadCommTime = 0.0f;  // Communication time from winning thread
	int winningThreadId = -1;
	
	// Find winning thread and extract timing values for multi-threaded algorithms
	if ( algorithm == 2 )
	{
		ParallelSudokuAntSystem* parallelSolver = dynamic_cast<ParallelSudokuAntSystem*>(solver);
		if ( parallelSolver )
		{
			const auto& subColonies = parallelSolver->GetSubColonies();
			int bestScore = 0;
			for ( size_t i = 0; i < subColonies.size(); i++ )
			{
				int score = subColonies[i]->GetBestSolScore();
				if ( score > bestScore )
				{
					bestScore = score;
					winningThreadId = (int)i;
					winningThreadCPTime = subColonies[i]->GetCPTime();
					winningThreadAntGuessingTime = subColonies[i]->GetAntGuessingTime();
					winningThreadCommTime = subColonies[i]->GetCommunicationTime();
				}
			}
		}
	}
	else if ( algorithm == 4 )
	{
		MultiThreadMultiColonyAntSystem* multiThreadSolver = dynamic_cast<MultiThreadMultiColonyAntSystem*>(solver);
		if ( multiThreadSolver )
		{
			const auto& threads = multiThreadSolver->GetThreads();
			int bestScore = 0;
			for ( size_t i = 0; i < threads.size(); i++ )
			{
				int score = threads[i]->GetBestSolScore();
				if ( score > bestScore )
				{
					bestScore = score;
					winningThreadId = (int)i;
					winningThreadCPTime = threads[i]->GetCPTime();
					winningThreadAntGuessingTime = threads[i]->GetAntGuessingTime();
					winningThreadCommTime = threads[i]->GetCommunicationTime();
					coopGameTime = threads[i]->GetCooperativeGameTime();
					pheromoneFusionTime = threads[i]->GetPheromoneFusionTime();
					publicPathTime = threads[i]->GetPublicPathRecommendationTime();
				}
			}
		}
	}
	else if ( algorithm == 3 )
	{
		MultiColonyAntSystem* multiColonySolver = dynamic_cast<MultiColonyAntSystem*>(solver);
		if ( multiColonySolver )
		{
			winningThreadCPTime = antCPTime;  // Single-threaded, use global
			winningThreadAntGuessingTime = multiColonySolver->GetAntGuessingTime();
			coopGameTime = multiColonySolver->GetCooperativeGameTime();
			pheromoneFusionTime = multiColonySolver->GetPheromoneFusionTime();
			publicPathTime = multiColonySolver->GetPublicPathRecommendationTime();
		}
	}
	else if ( algorithm == 0 )
	{
		SudokuAntSystem* antSolver = dynamic_cast<SudokuAntSystem*>(solver);
		if ( antSolver )
			winningThreadAntGuessingTime = antSolver->GetAntGuessingTime();
	}
	
	float totalCPTime = initialCPTime + winningThreadCPTime;

	int iterations = 0;
	bool communication = false;
	if ( algorithm == 0 )
	{
		SudokuAntSystem* antSolver = dynamic_cast<SudokuAntSystem*>(solver);
		if ( antSolver )
			iterations = antSolver->GetIterationsCompleted();
	}
	else if ( algorithm == 2 )
	{
		ParallelSudokuAntSystem* parallelSolver = dynamic_cast<ParallelSudokuAntSystem*>(solver);
		if ( parallelSolver )
		{
			iterations = parallelSolver->GetIterationsCompleted();
			communication = parallelSolver->GetCommunicationOccurred();
		}
	}
	else if ( algorithm == 3 )
	{
		MultiColonyAntSystem* multiColonySolver = dynamic_cast<MultiColonyAntSystem*>(solver);
		if ( multiColonySolver )
			iterations = multiColonySolver->GetIterationCount();
	}
	else if ( algorithm == 4 )
	{
		MultiThreadMultiColonyAntSystem* multiThreadSolver = dynamic_cast<MultiThreadMultiColonyAntSystem*>(solver);
		if ( multiThreadSolver )
		{
			iterations = multiThreadSolver->GetIterationsCompleted();
			communication = multiThreadSolver->GetCommunicationOccurred();
		}
	}
	
	if ( jsonOutput )
	{
		cout << fixed << setprecision(6);
		cout << "{";
		cout << "\"success\":" << (success ? "true" : "false") << ",";
		cout << "\"algorithm\":" << algorithm << ",";
		cout << "\"time\":" << solTime << ",";
		cout << "\"iterations\":" << iterations << ",";
		cout << "\"communication\":" << (communication ? "true" : "false") << ",";
		cout << "\"solution\":\"" << JsonEscape(solution.AsString(true)) << "\",";
		cout << "\"error\":\"" << JsonEscape(errorMessage) << "\",";
		cout << "\"cp_initial\":" << initialCPTime << ",";
		cout << "\"cp_ant\":" << winningThreadCPTime << ",";
		cout << "\"cp_calls\":" << cpCallCount << ",";
		cout << "\"cp_total\":" << totalCPTime;
		cout << "}" << endl;
		return 0;
	}

	// Output results
	if ( !verbose )
	{
		// Compact output format (for batch processing)
		cout << !success << endl << solTime << endl;
	}
	
	// Always output CP timing for parsing by scripts (both verbose and non-verbose)
	cout << "cp_initial: " << initialCPTime << endl;
	cout << "cp_ant: " << winningThreadCPTime << endl;
	cout << "cp_calls: " << cpCallCount << endl;
	
	if ( verbose )
	{
		// Verbose output format (for interactive use)
		if ( !success )
		{
			cout << "failed in time " << solTime << endl;
		}
		else
		{
			cout << "Solution:" << endl;
			string outString = solution.AsString(true);
			cout << outString << endl;
			cout << "solved in " << solTime << endl;
		}
		
		// Show iterations
		cout << "iterations: " << iterations << endl;
		
		// Show communication status and winning thread for multi-threaded algorithms
		if ( algorithm == 2 || algorithm == 4 )
		{
			cout << "communication: " << (communication ? "yes" : "no") << endl;
			if ( winningThreadId >= 0 )
				cout << "Thread: " << (winningThreadId + 1) << " winner" << endl;
		}
		
		// ====================================================================
		// TIME SECTION
		// ====================================================================
		cout << "\n==Time==" << endl;
		cout << fixed << setprecision(6);
		
		// Calculate percentages (avoid division by zero)
		float totalTime = (solTime > 0.0f) ? solTime : 1.0f;
		float initialCPPercent = (initialCPTime / totalTime) * 100.0f;
		float antCPPercent = (winningThreadCPTime / totalTime) * 100.0f;
		float antGuessingPercent = (winningThreadAntGuessingTime / totalTime) * 100.0f;
		float coopGamePercent = (coopGameTime / totalTime) * 100.0f;
		float fusionPercent = (pheromoneFusionTime / totalTime) * 100.0f;
		float publicPathPercent = (publicPathTime / totalTime) * 100.0f;
		float commPercent = (winningThreadCommTime / totalTime) * 100.0f;
		
		cout << "Initial CP Time: " << initialCPTime << " s (" << setprecision(2) << initialCPPercent << "%)" << endl;
		cout << fixed << setprecision(6);
		cout << "Ant CP Time: " << winningThreadCPTime << " s (" << setprecision(2) << antCPPercent << "%)" << endl;
		cout << fixed << setprecision(6);
		cout << "Ant Guessing Time: " << winningThreadAntGuessingTime << " s (" << setprecision(2) << antGuessingPercent << "%)" << endl;
		cout << fixed << setprecision(6);
		
		// Show multi-colony timing (algorithms 3 and 4)
		if ( algorithm == 3 || algorithm == 4 )
		{
			cout << "Coop Game Time: " << coopGameTime << " s (" << setprecision(2) << coopGamePercent << "%)" << endl;
			cout << fixed << setprecision(6);
			cout << "Pheromone Fusion Time: " << pheromoneFusionTime << " s (" << setprecision(2) << fusionPercent << "%)" << endl;
			cout << fixed << setprecision(6);
			cout << "Public Path Recom Time: " << publicPathTime << " s (" << setprecision(2) << publicPathPercent << "%)" << endl;
			cout << fixed << setprecision(6);
		}
		
		// Show communication time for multi-threaded algorithms
		if ( algorithm == 2 || algorithm == 4 )
		{
			cout << "Communication Between Threads Time: " << winningThreadCommTime << " s (" << setprecision(2) << commPercent << "%)" << endl;
			cout << fixed << setprecision(6);
		}
		
		cout << "Total Solve Time: " << solTime << " s" << endl;
	}
}
