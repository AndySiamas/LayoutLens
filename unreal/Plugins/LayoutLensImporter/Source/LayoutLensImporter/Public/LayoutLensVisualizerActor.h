#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LayoutLensRoomPlanTypes.h"
#include "LayoutLensVisualizerActor.generated.h"

UCLASS()
class LAYOUTLENSIMPORTER_API ALayoutLensVisualizerActor : public AActor
{
    GENERATED_BODY()

public:
    ALayoutLensVisualizerActor();

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    UFUNCTION(BlueprintCallable)
    bool ReloadLayout();

    FString GetRoomPlanFilePath() const;
    void SetRoomPlanFilePath(const FString& NewPath);

private:
    bool LoadJsonTextFromFile(FString& OutJsonText, FString& OutError) const;
    bool ParseRoomPlanJson(const FString& JsonText, FLayoutLensRoomPlan& OutPlan, FString& OutError) const;

    void ClearSpawnedActors();
    void SpawnRoomOutline(const FLayoutLensRoomPlan& Plan);
    void SpawnOpenings(const FLayoutLensRoomPlan& Plan);
    void SpawnFloorElements(const FLayoutLensRoomPlan& Plan);
    void SpawnWallMeshes(const FLayoutLensRoomPlan& Plan);

    FString GetAbsoluteFilePath(const FString& AnyPath) const;

    void ReloadLayoutHotkey();
    void BindReloadHotkey();

private:
    UPROPERTY(EditAnywhere, Category = "LayoutLens")
    FString RoomPlanFilePath;

    UPROPERTY(EditAnywhere, Category = "LayoutLens")
    bool SpawnWalls = true;

    UPROPERTY(EditAnywhere, Category = "LayoutLens")
    float WallThicknessCm = 10.0f;

    UPROPERTY(EditAnywhere, Category = "LayoutLens")
    bool AutoLoadOnBeginPlay = true;

    UPROPERTY(EditAnywhere, Category = "LayoutLens")
    bool ShowOverlay = true;

    UPROPERTY(EditAnywhere, Category = "LayoutLens")
    bool DrawRoomBoundary = true;

    UPROPERTY(EditAnywhere, Category = "LayoutLens")
    bool DrawOpenings = true;

    UPROPERTY(EditAnywhere, Category = "LayoutLens")
    bool SpawnLabels = true;

    UPROPERTY()
    TArray<TObjectPtr<AActor>> SpawnedActors;

    TSharedPtr<class SWidget> OverlayWidget;
    TSharedPtr<class SWeakWidget> OverlayContainer;
};