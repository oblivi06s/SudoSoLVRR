#include "sudokuant.h"
#include "sudokuantsystem.h"
#include "constraintpropagation.h"
#include <chrono>

void SudokuAnt::InitSolution(const Board &puzzle, int startCell )
{
	sol.Copy(puzzle);
	iCell = startCell;
	failCells = 0;
	if (roulette != nullptr)
	{
		delete[] roulette;
		delete[] rouletteVals;
	}
	roulette = new float[puzzle.GetNumUnits()];
	rouletteVals = new ValueSet[puzzle.GetNumUnits()];
}

void SudokuAnt::StepSolution()
{
	if (sol.GetCell(iCell).Empty())
	{
		failCells++;
	}
	else if ( !sol.GetCell(iCell).Fixed() )
	{
		// Time the decision-making phase (ant guessing)
		auto guessingStartTime = std::chrono::steady_clock::now();
		
		// make a choice from the options
		ValueSet choice = ValueSet(sol.GetNumUnits(), 1);
		if (parent->random() < parent->Getq0())
		{
			// greedy selection
			ValueSet best;
			float maxPher = -1.0f;

			for (int i = 0; i < sol.GetNumUnits(); i++)
			{
				if (sol.GetCell(iCell).Contains(choice))
				{
					if (parent->Pher(iCell, i) > maxPher)
					{
						maxPher = parent->Pher(iCell, i);
						best = choice;
					}
				}
				choice <<= 1;
			}
			
			// End timing for decision-making
			auto guessingEndTime = std::chrono::steady_clock::now();
			auto guessingDuration = std::chrono::duration_cast<std::chrono::duration<double>>(guessingEndTime - guessingStartTime);
			float guessingElapsed = (float)guessingDuration.count();
			CP::AddAntGuessingTime(guessingElapsed);
			
			SetCellAndPropagate(sol, iCell, best);
			// do local pheromone update here
			parent->LocalPheromoneUpdate(iCell, best.Index());
		}
		else
		{
			// weighted selection
			float totPher = 0.0f;
			int numChoices = 0;
			for (int i = 0; i < sol.GetNumUnits(); i++)
			{
				if (sol.GetCell(iCell).Contains(choice))
				{
					roulette[numChoices] = totPher + parent->Pher(iCell, i);
					totPher = roulette[numChoices];
					rouletteVals[numChoices] = choice;
					++numChoices;
				}
				choice <<= 1;
			}
			float rouletteVal = totPher * parent->random();

			for (int i = 0; i < numChoices; i++)
			{
				if (roulette[i] > rouletteVal)
				{
					// End timing for decision-making
					auto guessingEndTime = std::chrono::steady_clock::now();
					auto guessingDuration = std::chrono::duration_cast<std::chrono::duration<double>>(guessingEndTime - guessingStartTime);
					float guessingElapsed = (float)guessingDuration.count();
					CP::AddAntGuessingTime(guessingElapsed);
					
					SetCellAndPropagate(sol, iCell, rouletteVals[i]);
					// do local pheromone update here
					parent->LocalPheromoneUpdate(iCell, rouletteVals[i].Index());
					break;
				}
			}
		}
	}
	++iCell;
	if (iCell == sol.CellCount()) // wrap around
		iCell = 0;
}

