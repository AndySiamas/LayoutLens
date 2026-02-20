#pragma once

#include "CoreMinimal.h"
#include "LayoutLensRoomPlanTypes.generated.h"

USTRUCT()
struct FLayoutLensPoint2D
{
    GENERATED_BODY()

    float X = 0.0f;
    float Y = 0.0f;
};

USTRUCT()
struct FLayoutLensTransform2D
{
    GENERATED_BODY()

    float X = 0.0f;
    float Y = 0.0f;
    float YawDeg = 0.0f;
};

USTRUCT()
struct FLayoutLensElement
{
    GENERATED_BODY()

    FString Id;
    FString Label;
    FString Placement;

    float HeightMeters = 0.9f;

    FLayoutLensTransform2D Transform;

    FString FootprintKind;
    float WidthMeters = 1.0f;
    float DepthMeters = 1.0f;

    TArray<FLayoutLensPoint2D> PolygonPoints;
};

USTRUCT()
struct FLayoutLensOpening
{
    GENERATED_BODY()

    FString Kind;
    int32 EdgeIndex = 0;
    float Center01 = 0.5f;
    float WidthMeters = 1.0f;
};

USTRUCT()
struct FLayoutLensRoomPlan
{
    GENERATED_BODY()

    float RoomHeightMeters = 2.7f;
    TArray<FLayoutLensPoint2D> Boundary;
    TArray<FLayoutLensOpening> Openings;
    TArray<FLayoutLensElement> Elements;
};