#include "multicolonyantsystem.h"
#include "constraintpropagation.h"
#include <iostream>
#include <algorithm>
#include <climits>
#include <limits>
#include <cmath>
#include <chrono>

void MultiColonyAntSystem::InitPheromone(Colony &c, int nNumCells, int valuesPerCell)
{
    c.numCells = nNumCells;
    c.valuesPerCell = valuesPerCell;
    c.pher = new float *[c.numCells];
    for (int i = 0; i < c.numCells; i++)
    {
        c.pher[i] = new float[valuesPerCell];
        for (int j = 0; j < valuesPerCell; j++)
            c.pher[i][j] = pher0;
    }
}

void MultiColonyAntSystem::ClearPheromone(Colony &c)
{
    for (int i = 0; i < c.numCells; i++)
        delete[] c.pher[i];
    delete[] c.pher;
    c.pher = nullptr;
}

float MultiColonyAntSystem::PherAdd(int numCells, int cellsFilled)
{
    return numCells / (float)(numCells - cellsFilled);
}

void MultiColonyAntSystem::UpdatePheromone(int colonyIdx, Colony &c, const Board &bestSol, float bestPher)
{
    for (int i = 0; i < c.numCells; i++)
    {
        if (bestSol.GetCell(i).Fixed())
        {
            int idx = bestSol.GetCell(i).Index();
            float r = GetRho(colonyIdx);
            c.pher[i][idx] = c.pher[i][idx] * (1.0f - r) + r * bestPher;
        }
    }
    ClampPheromone(c);
}

bool MultiColonyAntSystem::Solve(const Board &puzzle, float maxTime)
{
    solutionTimer.Reset();
    dcmAcoTimer.Reset();
    int iter = 0;
    bool solved = false;
    const int nACS = (std::min)(numACS, numColonies);
    
    // Reset timing counters
    dcmAcoTime = 0.0f;
    cooperativeGameTime = 0.0f;
    pheromoneFusionTime = 0.0f;
    publicPathRecommendationTime = 0.0f;

    // init colonies
    colonyQ0.resize(numColonies);
    colonyRho.resize(numColonies);
    for (int c = 0; c < numColonies; ++c)
    {
        InitPheromone(colonies[c], puzzle.CellCount(), puzzle.GetNumUnits());
        colonies[c].bestPher = 0.0f;
        colonies[c].bestVal = 0;
        colonies[c].tau0 = pher0;
        // assign colony type: 2 ACS, 1 MMAS (for DCM-ACO)
        colonies[c].type = (c < nACS ? 0 : 1);
        // Parameters per colony type:
        //  - ACS colonies (first 2): use ACS q0 and rho from Lloyd & Amos ACS style
        //  - MMAS colony (remaining 1): pure roulette (q0 = 0), rho fixed to 0.1 as per paper
        if (colonies[c].type == 0)
        {
            colonyQ0[c] = q0;
            colonyRho[c] = rho;
        }
        else
        {
            colonyQ0[c] = 0.0f;
            colonyRho[c] = 0.1f;
        }
        // initial Max-Min bounds (used by MMAS colonies)
        // Initialize with initial pheromone value
        if (colonies[c].type == 1) // MMAS
        {
            float rho_mmas = colonyRho[c]; // 0.1 for MMAS
            float best_pheromone_toAdd = pher0; // initial estimate
            float n = (float)puzzle.GetNumUnits(); // puzzle size (e.g., 9 for 9x9)
            colonies[c].tauMax = best_pheromone_toAdd / rho_mmas;
            colonies[c].tauMin = colonies[c].tauMax / (2.0f * n);
        }
        else // ACS colonies can keep simple initial bounds
        {
            colonies[c].tauMax = colonies[c].tau0 * 10.0f;
            colonies[c].tauMin = colonies[c].tau0 * 0.01f;
        }
        colonies[c].lastImproveIter = 0;
        // create ants
        for (int i = 0; i < antsPerColony; i++)
            colonies[c].ants.push_back(new ColonyAnt(this, c));
    }

    std::uniform_int_distribution<int> startDist(0, puzzle.CellCount() - 1);

    while (!solved)
    {
        // init ant solutions with different starts
        for (int c = 0; c < numColonies; ++c)
        {
            for (auto *a : colonies[c].ants)
                a->InitSolution(puzzle, startDist(randGen));
        }

        // construct solutions cell by cell
        for (int i = 0; i < puzzle.CellCount(); i++)
        {
            for (int c = 0; c < numColonies; ++c)
            {
                for (auto *a : colonies[c].ants)
                    a->StepSolution();
            }
        }

        // per-colony: evaluate bests and track global best
        for (int c = 0; c < numColonies; ++c)
        {
            int iBest = 0;
            int bestVal = 0;
            auto &ants = colonies[c].ants;
            for (unsigned int i = 0; i < ants.size(); i++)
            {
                if (ants[i]->NumCellsFilled() > bestVal)
                {
                    bestVal = ants[i]->NumCellsFilled();
                    iBest = (int)i;
                }
            }
            float pherToAdd = PherAdd(colonies[c].numCells, bestVal);
            if (pherToAdd > colonies[c].bestPher)
            {
                colonies[c].bestSol.Copy(ants[iBest]->GetSolution());
                colonies[c].bestPher = pherToAdd;
                colonies[c].bestVal = bestVal;
                colonies[c].lastImproveIter = iter;
                // Update Max-Min bounds with improvement (for MMAS colonies)
                if (colonies[c].type == 1)
                {
                    // τ_max = best_pheromone_toAdd / ρ
                    // τ_min = τ_max / (2n) where n is the puzzle size (e.g., 9 for 9x9)
                    float rho_mmas = GetRho(c); // Should be 0.1 for MMAS
                    float best_pheromone_toAdd = colonies[c].bestPher; // best pheromone value
                    float n = (float)colonies[c].valuesPerCell; // puzzle size (e.g., 9 for 9x9)
                    
                    colonies[c].tauMax = best_pheromone_toAdd / rho_mmas;
                    colonies[c].tauMin = colonies[c].tauMax / (2.0f * n);
                }
            }
            // update global best
            if (colonies[c].bestPher > globalBestPher)
            {
                globalBestPher = colonies[c].bestPher;
                globalBestSol.Copy(colonies[c].bestSol);
                globalBestVal = colonies[c].bestVal;
                if (globalBestVal == puzzle.CellCount())
                {
                    solved = true;
                    solTime = solutionTimer.Elapsed();
                }
            }
        }

        // partition indices by type
        std::vector<int> acsIdx; acsIdx.reserve(numColonies);
        std::vector<int> mmasIdx; mmasIdx.reserve(numColonies);
        for (int c = 0; c < numColonies; ++c)
            (colonies[c].type == 0 ? acsIdx : mmasIdx).push_back(c);

        // Check ACS entropy: if < threshold -> pheromone fusion, else -> cooperative game (paper pseudocode)
        std::vector<float> acsAllocated; acsAllocated.resize(numColonies, 0.0f);
        if (!acsIdx.empty())
        {
            bool hasLowEntropy = false;
            for (int cidx : acsIdx)
            {
                if (ComputeEntropy(colonies[cidx]) < entropyThreshold)
                {
                    hasLowEntropy = true;
                    break;
                }
            }
            if (hasLowEntropy)
            {
                // Time Pheromone Fusion
                auto startTime = std::chrono::steady_clock::now();
                ApplyPheromoneFusion(acsIdx, mmasIdx);
                auto endTime = std::chrono::steady_clock::now();
                auto duration = std::chrono::duration_cast<std::chrono::duration<double>>(endTime - startTime);
                pheromoneFusionTime += (float)duration.count();
            }
            else
            {
                // Time Cooperative Game Theory
                auto startTime = std::chrono::steady_clock::now();
                ACSCooperativeGameAllocate(acsIdx, acsAllocated);
                auto endTime = std::chrono::steady_clock::now();
                auto duration = std::chrono::duration_cast<std::chrono::duration<double>>(endTime - startTime);
                cooperativeGameTime += (float)duration.count();
            }
        }

        // Apply pheromone updates per type
        for (int c : acsIdx)
        {
            float add = (acsAllocated[c] > 0.0f) ? acsAllocated[c] : colonies[c].bestPher;
            UpdatePheromone(c, colonies[c], colonies[c].bestSol, add);
            colonies[c].bestPher *= (1.0f - bestEvap);
        }
        for (int c : mmasIdx)
        {
            UpdatePheromone(c, colonies[c], colonies[c].bestSol, colonies[c].bestPher);
            // colonies[c].bestPher *= (1.0f - bestEvap); 
        }

        // Public path recommendation (only applied when convergence speed is low, checked inside function)
        {
            // Time Public Path Recommendation
            auto startTime = std::chrono::steady_clock::now();
            ApplyPublicPathRecommendation(iter, acsIdx, mmasIdx);
            auto endTime = std::chrono::steady_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::duration<double>>(endTime - startTime);
            publicPathRecommendationTime += (float)duration.count();
        }

        ++iter;
        if ((iter % 100) == 0)
        {
            float elapsed = solutionTimer.Elapsed();
            if (elapsed > maxTime)
                break;
        }
    }

    for (int c = 0; c < numColonies; ++c)
        ClearPheromone(colonies[c]);
    
    iterationCount = iter;
    
    // Always capture solution time, regardless of success/failure
    solTime = solutionTimer.Elapsed();
    
    // Get the DCM-ACO time (will be calculated by subtraction in solvermain.cpp)
    dcmAcoTime = dcmAcoTimer.Elapsed();
    
    std::cout << "Number of cycles (multi): " << iter << "\n";
    return solved;
}

void MultiColonyAntSystem::ClampPheromone(Colony &c)
{
    if (c.type == 1) // MMAS only
    {
        for (int i = 0; i < c.numCells; ++i)
            for (int j = 0; j < c.valuesPerCell; ++j)
            {
                if (c.pher[i][j] < c.tauMin) c.pher[i][j] = c.tauMin;
                else if (c.pher[i][j] > c.tauMax) c.pher[i][j] = c.tauMax;
            }
    }
}

// Shannon entropy of pheromone distribution for a colony
float MultiColonyAntSystem::ComputeEntropy(const Colony &c) const
{
    double sum = 0.0;
    for (int i = 0; i < c.numCells; ++i)
        for (int j = 0; j < c.valuesPerCell; ++j)
            sum += c.pher[i][j];
    if (sum <= 0.0) return 0.0f;
    double H = 0.0;
    for (int i = 0; i < c.numCells; ++i)
    {
        for (int j = 0; j < c.valuesPerCell; ++j)
        {
            double p = c.pher[i][j] / sum;
            if (p > 0.0)
                H -= p * std::log(p);
        }
    }
    return (float)H;
}

// Cooperative game allocation among ACS colonies
void MultiColonyAntSystem::ACSCooperativeGameAllocate(std::vector<int> &acsIdx,
                                                      std::vector<float> &allocatedBestPher)
{
    if (acsIdx.empty()) return;
    // total payoff b = sum of per-ACS pheromone revenues (use PherAdd from bestVal)
    double b = 0.0;
    int minLen = (std::numeric_limits<int>::max)();
    std::vector<int> lengths; lengths.reserve(acsIdx.size());
    std::vector<float> entropies; entropies.reserve(acsIdx.size());
    float emax = 0.0f;
    for (int idx : acsIdx)
    {
        int len = colonies[idx].numCells - colonies[idx].bestVal; // lower is better
        lengths.push_back(len);
        if (len < minLen) minLen = len;
        float add = PherAdd(colonies[idx].numCells, colonies[idx].bestVal);
        b += add;
        float e = ComputeEntropy(colonies[idx]);
        entropies.push_back(e);
        if (e > emax) emax = e;
    }
    // contributions
    double sumContr = 0.0;
    std::vector<double> contr(acsIdx.size(), 0.0);
    for (size_t k = 0; k < acsIdx.size(); ++k)
    {
        double soli = (lengths[k] > 0 ? ((double)minLen / (double)lengths[k]) : 1.0);
        double Hi = (emax > 0.0f ? (entropies[k] / emax) : 0.0);
        contr[k] = soli * Hi;
        sumContr += contr[k];
    }
    // allocate new pheromone revenue per ACS
    for (size_t k = 0; k < acsIdx.size(); ++k)
    {
        double ihat = (sumContr > 0.0 ? contr[k] / sumContr : (1.0 / (double)acsIdx.size()));
        allocatedBestPher[acsIdx[k]] = (float)(ihat * b);
    }
}

// Mix ACS pheromone with MMAS pheromone when ACS entropy below fixed threshold (E(p)* = 4)
void MultiColonyAntSystem::ApplyPheromoneFusion(const std::vector<int> &acsIdx,
                                                const std::vector<int> &mmasIdx)
{
    if (acsIdx.empty() || mmasIdx.empty()) return;
    // compute average MMAS entropy and average MMAS pheromone matrix
    // build average pheromone matrix of MMAS
    int nc = colonies[mmasIdx[0]].numCells;
    int vp = colonies[mmasIdx[0]].valuesPerCell;
    std::vector<float> avg(nc * vp, 0.0f);
    for (int cidx : mmasIdx)
    {
        for (int i = 0; i < nc; ++i)
            for (int j = 0; j < vp; ++j)
                avg[i*vp + j] += colonies[cidx].pher[i][j];
    }
    for (auto &v : avg) v /= (float)mmasIdx.size();
    // entropy of averaged MMAS matrix
    Colony tmp;
    tmp.pher = new float*[nc];
    tmp.numCells = nc; tmp.valuesPerCell = vp;
    for (int i = 0; i < nc; ++i)
    {
        tmp.pher[i] = new float[vp];
        for (int j = 0; j < vp; ++j) tmp.pher[i][j] = avg[i*vp + j];
    }
    float eMMAS = ComputeEntropy(tmp);
    for (int i = 0; i < nc; ++i) delete [] tmp.pher[i];
    delete [] tmp.pher; tmp.pher = nullptr;

    float eThresh = entropyThreshold;

    for (int cidx : acsIdx)
    {
        float eACS = ComputeEntropy(colonies[cidx]);
        if (eACS < eThresh)
        {
            // Base mix weight from entropies: Wi = E(ACS)/(E(ACS)+E(MMAS))
            float mix = (eACS + eMMAS > 0.0f ? (eACS / (eACS + eMMAS)) : 0.0f);
            // ph_i <- (1 - mix)*ph_i + mix*ph_mmas_avg
            for (int i = 0; i < nc; ++i)
            {
                for (int j = 0; j < vp; ++j)
                {
                    colonies[cidx].pher[i][j] = (1.0f - mix) * colonies[cidx].pher[i][j] + mix * avg[i*vp + j];
                }
            }
        }
    }
}

// Recommend public paths from ACS to MMAS when MMAS convergence is slow
void MultiColonyAntSystem::ApplyPublicPathRecommendation(int iter,
                                                         const std::vector<int> &acsIdx,
                                                         const std::vector<int> &mmasIdx)
{
    if (acsIdx.empty() || mmasIdx.empty()) return;
    // Build public assignments: intersection of ACS best solutions' fixed cells
    int nc = colonies[acsIdx[0]].numCells;
    int vp = colonies[acsIdx[0]].valuesPerCell;
    std::vector<int> publicIdx(nc, -1);
    for (int cell = 0; cell < nc; ++cell)
    {
        bool allAgree = true;
        int agreeIdx = -1;
        for (size_t k = 0; k < acsIdx.size(); ++k)
        {
            const Board &b = colonies[acsIdx[k]].bestSol;
            if (!b.GetCell(cell).Fixed()) { allAgree = false; break; }
            int idx = b.GetCell(cell).Index();
            if (k == 0) agreeIdx = idx;
            else if (idx != agreeIdx) { allAgree = false; break; }
        }
        if (allAgree) publicIdx[cell] = agreeIdx;
    }

    // reinforcement amount: 1 / (n * e^iter) (paper constant)
    float n = (float)nc;
    float tauPub = std::exp(-(float)iter) / n;

    for (int cidx : mmasIdx)
    {
        // convergence rate con_t = iter_opt / iter_t
        float con_t = (iter > 0 ? ((float)colonies[cidx].lastImproveIter / (float)iter) : 1.0f);
        float threshold = this->convThreshold;
        if (con_t < threshold)
        {
            for (int cell = 0; cell < nc; ++cell)
            {
                int idx = publicIdx[cell];
                if (idx >= 0)
                {
                    colonies[cidx].pher[cell][idx] += tauPub;
                }
            }
            ClampPheromone(colonies[cidx]);
        }
    }
}