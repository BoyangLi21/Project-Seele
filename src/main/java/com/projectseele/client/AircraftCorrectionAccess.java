package com.projectseele.client;

public interface AircraftCorrectionAccess
{
    double projectSeele$aircraftCorrectionBudget(long elapsedMillis,double metresPerSecond);
    String projectSeele$aircraftTimingState();
    int projectSeele$coordinateEpoch();
}
