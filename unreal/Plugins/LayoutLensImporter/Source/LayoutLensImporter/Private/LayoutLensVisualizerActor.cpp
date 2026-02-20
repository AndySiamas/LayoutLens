#include "LayoutLensVisualizerActor.h"

#include "LayoutLensPlaceholderActor.h"
#include "SSLayoutLensOverlayWidget.h"

#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "DrawDebugHelpers.h"
#include "InputCoreTypes.h"
#include "Json.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Widgets/SWeakWidget.h"

ALayoutLensVisualizerActor::ALayoutLensVisualizerActor()
{
    PrimaryActorTick.bCanEverTick = false;

    RoomPlanFilePath = TEXT("output/latest/room_plan.json");
}

void ALayoutLensVisualizerActor::BeginPlay()
{
    Super::BeginPlay();

    BindReloadHotkey();

    if (ShowOverlay && GEngine != nullptr && GEngine->GameViewport != nullptr)
    {
        const TSharedRef<SLayoutLensOverlayWidget> NewOverlayWidget =
            SNew(SLayoutLensOverlayWidget).VisualizerActor(this);

        OverlayWidget = NewOverlayWidget;

        OverlayContainer = SNew(SWeakWidget).PossiblyNullContent(OverlayWidget.ToSharedRef());

        GEngine->GameViewport->AddViewportWidgetContent(OverlayContainer.ToSharedRef(), 50);
    }

    if (AutoLoadOnBeginPlay)
    {
        ReloadLayout();
    }
}

void ALayoutLensVisualizerActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (GEngine != nullptr && GEngine->GameViewport != nullptr && OverlayContainer.IsValid())
    {
        GEngine->GameViewport->RemoveViewportWidgetContent(OverlayContainer.ToSharedRef());
    }

    ClearSpawnedActors();

    Super::EndPlay(EndPlayReason);
}

FString ALayoutLensVisualizerActor::GetRoomPlanFilePath() const
{
    return RoomPlanFilePath;
}

void ALayoutLensVisualizerActor::SetRoomPlanFilePath(const FString& NewPath)
{
    RoomPlanFilePath = NewPath;
}

bool ALayoutLensVisualizerActor::ReloadLayout()
{
    ClearSpawnedActors();

    FString JsonText;
    FString ErrorText;

    const bool bLoaded = LoadJsonTextFromFile(JsonText, ErrorText);
    if (!bLoaded)
    {
        UE_LOG(LogTemp, Error, TEXT("LayoutLens: Failed to load file. %s"), *ErrorText);
        return false;
    }

    FLayoutLensRoomPlan Plan;
    const bool bParsed = ParseRoomPlanJson(JsonText, Plan, ErrorText);
    if (!bParsed)
    {
        UE_LOG(LogTemp, Error, TEXT("LayoutLens: Failed to parse JSON. %s"), *ErrorText);
        return false;
    }

    if (DrawRoomBoundary)
    {
        SpawnRoomOutline(Plan);
    }

    if (SpawnWalls)
    {
        SpawnWallMeshes(Plan);
    }

    if (DrawOpenings)
    {
        SpawnOpenings(Plan);
    }

    SpawnFloorElements(Plan);

    UE_LOG(LogTemp, Log, TEXT("LayoutLens: Loaded %d elements."), Plan.Elements.Num());
    return true;
}

bool ALayoutLensVisualizerActor::LoadJsonTextFromFile(FString& OutJsonText, FString& OutError) const
{
    const FString AbsolutePath = GetAbsoluteFilePath(RoomPlanFilePath);

    if (!FPaths::FileExists(AbsolutePath))
    {
        OutError = FString::Printf(TEXT("File not found: %s"), *AbsolutePath);
        return false;
    }

    const bool bOk = FFileHelper::LoadFileToString(OutJsonText, *AbsolutePath);
    if (!bOk)
    {
        OutError = FString::Printf(TEXT("LoadFileToString failed: %s"), *AbsolutePath);
        return false;
    }

    return true;
}

FString ALayoutLensVisualizerActor::GetAbsoluteFilePath(const FString& AnyPath) const
{
    FString CleanPath = AnyPath;
    CleanPath.TrimStartAndEndInline();

    if (FPaths::IsRelative(CleanPath))
    {
        const FString FullPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir(), CleanPath);
        return FullPath;
    }

    return CleanPath;
}

bool ALayoutLensVisualizerActor::ParseRoomPlanJson(const FString& JsonText, FLayoutLensRoomPlan& OutPlan, FString& OutError) const
{
    TSharedPtr<FJsonObject> RootObject;

    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonText);
    const bool bOk = FJsonSerializer::Deserialize(Reader, RootObject);
    if (!bOk || !RootObject.IsValid())
    {
        OutError = TEXT("FJsonSerializer::Deserialize failed.");
        return false;
    }

    const TSharedPtr<FJsonObject>* SpaceObjectPointer = nullptr;

    if (!RootObject->TryGetObjectField(TEXT("space"), SpaceObjectPointer) ||
        SpaceObjectPointer == nullptr || !SpaceObjectPointer->IsValid())
    {
        OutError = TEXT("Missing 'space' object.");
        return false;
    }

    const TSharedPtr<FJsonObject>& SpaceObject = *SpaceObjectPointer;

    OutPlan.RoomHeightMeters = (float)SpaceObject->GetNumberField(TEXT("height"));

    const TArray<TSharedPtr<FJsonValue>>* BoundaryArray = nullptr;
    if (!SpaceObject->TryGetArrayField(TEXT("boundary"), BoundaryArray) || BoundaryArray == nullptr)
    {
        OutError = TEXT("Missing 'space.boundary' array.");
        return false;
    }

    OutPlan.Boundary.Empty();
    for (const TSharedPtr<FJsonValue>& PointValue : *BoundaryArray)
    {
        const TSharedPtr<FJsonObject> PointObject = PointValue->AsObject();
        if (!PointObject.IsValid())
        {
            continue;
        }

        FLayoutLensPoint2D Point;
        Point.X = (float)PointObject->GetNumberField(TEXT("x"));
        Point.Y = (float)PointObject->GetNumberField(TEXT("y"));
        OutPlan.Boundary.Add(Point);
    }

    const TArray<TSharedPtr<FJsonValue>>* OpeningsArray = nullptr;
    if (SpaceObject->TryGetArrayField(TEXT("openings"), OpeningsArray) && OpeningsArray != nullptr)
    {
        OutPlan.Openings.Empty();
        for (const TSharedPtr<FJsonValue>& OpeningValue : *OpeningsArray)
        {
            const TSharedPtr<FJsonObject> OpeningObject = OpeningValue->AsObject();
            if (!OpeningObject.IsValid())
            {
                continue;
            }

            FLayoutLensOpening Opening;
            Opening.Kind = OpeningObject->GetStringField(TEXT("kind"));
            Opening.EdgeIndex = OpeningObject->GetIntegerField(TEXT("edge_index"));
            Opening.Center01 = (float)OpeningObject->GetNumberField(TEXT("center"));
            Opening.WidthMeters = (float)OpeningObject->GetNumberField(TEXT("width"));
            OutPlan.Openings.Add(Opening);
        }
    }

    const TArray<TSharedPtr<FJsonValue>>* ElementsArray = nullptr;
    if (!RootObject->TryGetArrayField(TEXT("elements"), ElementsArray) || ElementsArray == nullptr)
    {
        OutError = TEXT("Missing 'elements' array.");
        return false;
    }

    OutPlan.Elements.Empty();

    for (const TSharedPtr<FJsonValue>& ElementValue : *ElementsArray)
    {
        const TSharedPtr<FJsonObject> ElementObject = ElementValue->AsObject();
        if (!ElementObject.IsValid())
        {
            continue;
        }

        FLayoutLensElement Element;
        Element.Id = ElementObject->GetStringField(TEXT("id"));
        Element.Label = ElementObject->GetStringField(TEXT("label"));
        Element.Placement = ElementObject->GetStringField(TEXT("placement"));
        Element.HeightMeters = (float)ElementObject->GetNumberField(TEXT("height"));

        const TSharedPtr<FJsonObject>* TransformObjectPointer = nullptr;
        if (ElementObject->TryGetObjectField(TEXT("transform"), TransformObjectPointer) &&
            TransformObjectPointer != nullptr && TransformObjectPointer->IsValid())
        {
            const TSharedPtr<FJsonObject>& TransformObject = *TransformObjectPointer;
            Element.Transform.X = (float)TransformObject->GetNumberField(TEXT("x"));
            Element.Transform.Y = (float)TransformObject->GetNumberField(TEXT("y"));
            Element.Transform.YawDeg = (float)TransformObject->GetNumberField(TEXT("yaw_deg"));
        }

        const TSharedPtr<FJsonObject>* FootprintObjectPointer = nullptr;
        if (ElementObject->TryGetObjectField(TEXT("footprint"), FootprintObjectPointer) &&
            FootprintObjectPointer != nullptr && FootprintObjectPointer->IsValid())
        {
            const TSharedPtr<FJsonObject>& FootprintObject = *FootprintObjectPointer;
            Element.FootprintKind = FootprintObject->GetStringField(TEXT("kind"));

            if (Element.FootprintKind.Equals(TEXT("rect"), ESearchCase::IgnoreCase))
            {
                Element.WidthMeters = (float)FootprintObject->GetNumberField(TEXT("width"));
                Element.DepthMeters = (float)FootprintObject->GetNumberField(TEXT("depth"));
            }
            else if (Element.FootprintKind.Equals(TEXT("poly"), ESearchCase::IgnoreCase))
            {
                const TArray<TSharedPtr<FJsonValue>>* PointsArray = nullptr;
                if (FootprintObject->TryGetArrayField(TEXT("points"), PointsArray) && PointsArray != nullptr)
                {
                    Element.PolygonPoints.Empty();

                    for (const TSharedPtr<FJsonValue>& PolyPointValue : *PointsArray)
                    {
                        const TSharedPtr<FJsonObject> PolyPointObject = PolyPointValue->AsObject();
                        if (!PolyPointObject.IsValid())
                        {
                            continue;
                        }

                        FLayoutLensPoint2D PolyPoint;
                        PolyPoint.X = (float)PolyPointObject->GetNumberField(TEXT("x"));
                        PolyPoint.Y = (float)PolyPointObject->GetNumberField(TEXT("y"));
                        Element.PolygonPoints.Add(PolyPoint);
                    }

                    float MinX = 0.0f;
                    float MaxX = 0.0f;
                    float MinY = 0.0f;
                    float MaxY = 0.0f;

                    if (Element.PolygonPoints.Num() > 0)
                    {
                        MinX = Element.PolygonPoints[0].X;
                        MaxX = Element.PolygonPoints[0].X;
                        MinY = Element.PolygonPoints[0].Y;
                        MaxY = Element.PolygonPoints[0].Y;

                        for (const FLayoutLensPoint2D& P : Element.PolygonPoints)
                        {
                            MinX = FMath::Min(MinX, P.X);
                            MaxX = FMath::Max(MaxX, P.X);
                            MinY = FMath::Min(MinY, P.Y);
                            MaxY = FMath::Max(MaxY, P.Y);
                        }

                        Element.WidthMeters = FMath::Max(MaxX - MinX, 0.01f);
                        Element.DepthMeters = FMath::Max(MaxY - MinY, 0.01f);
                    }
                }
            }
        }

        OutPlan.Elements.Add(Element);
    }

    return true;
}

void ALayoutLensVisualizerActor::ClearSpawnedActors()
{
    for (AActor* Actor : SpawnedActors)
    {
        if (Actor != nullptr)
        {
            Actor->Destroy();
        }
    }
    SpawnedActors.Empty();
}

void ALayoutLensVisualizerActor::SpawnRoomOutline(const FLayoutLensRoomPlan& Plan)
{
    const float Z = 5.0f;
    const int32 Count = Plan.Boundary.Num();
    if (Count < 2)
    {
        return;
    }

    for (int32 Index = 0; Index < Count; Index++)
    {
        const int32 NextIndex = (Index + 1) % Count;

        const FVector A = FVector(Plan.Boundary[Index].X * 100.0f, Plan.Boundary[Index].Y * 100.0f, Z);
        const FVector B = FVector(Plan.Boundary[NextIndex].X * 100.0f, Plan.Boundary[NextIndex].Y * 100.0f, Z);

        DrawDebugLine(GetWorld(), A, B, FColor::Cyan, true, 0.0f, 100, 4.0f);
    }
}

void ALayoutLensVisualizerActor::SpawnOpenings(const FLayoutLensRoomPlan& Plan)
{
    const int32 PointCount = Plan.Boundary.Num();
    if (PointCount < 2)
    {
        return;
    }

    const float RoomHeightCm = Plan.RoomHeightMeters * 100.0f;
    const float WallOffsetCm = (WallThicknessCm * 0.5f) + 2.0f;

    for (const FLayoutLensOpening& Opening : Plan.Openings)
    {
        const int32 EdgeIndex = FMath::Clamp(Opening.EdgeIndex, 0, PointCount - 1);
        const int32 NextIndex = (EdgeIndex + 1) % PointCount;

        const FVector EdgeA = FVector(Plan.Boundary[EdgeIndex].X * 100.0f, Plan.Boundary[EdgeIndex].Y * 100.0f, 0.0f);
        const FVector EdgeB = FVector(Plan.Boundary[NextIndex].X * 100.0f, Plan.Boundary[NextIndex].Y * 100.0f, 0.0f);

        FVector EdgeDelta = EdgeB - EdgeA;
        EdgeDelta.Z = 0.0f;

        const float EdgeLengthCm = EdgeDelta.Size();
        if (EdgeLengthCm < 1.0f)
        {
            continue;
        }

        const FVector EdgeDirectionUnit = EdgeDelta / EdgeLengthCm;
        const FVector WallNormalUnit = FVector(-EdgeDirectionUnit.Y, EdgeDirectionUnit.X, 0.0f).GetSafeNormal();

        const float CenterDistanceCm = FMath::Clamp(Opening.Center01, 0.0f, 1.0f) * EdgeLengthCm;
        const FVector CenterPoint = EdgeA + (EdgeDirectionUnit * CenterDistanceCm) + (WallNormalUnit * WallOffsetCm);

        const float HalfWidthCm = (Opening.WidthMeters * 100.0f) * 0.5f;
        const FVector A2D = CenterPoint - (EdgeDirectionUnit * HalfWidthCm);
        const FVector B2D = CenterPoint + (EdgeDirectionUnit * HalfWidthCm);

        const bool IsDoor = Opening.Kind.Equals(TEXT("door"), ESearchCase::IgnoreCase);
        const bool IsWindow = Opening.Kind.Equals(TEXT("window"), ESearchCase::IgnoreCase);

        float BottomZCm = 0.0f;
        float TopZCm = 150.0f;

        if (IsDoor)
        {
            BottomZCm = 0.0f;
            TopZCm = FMath::Min(RoomHeightCm, 210.0f);
        }
        else if (IsWindow)
        {
            const float SillZCm = 100.0f;
            const float WindowHeightCm = 100.0f;

            BottomZCm = FMath::Clamp(SillZCm, 0.0f, FMath::Max(RoomHeightCm - 20.0f, 0.0f));
            TopZCm = FMath::Min(RoomHeightCm - 10.0f, BottomZCm + WindowHeightCm);
        }
        else
        {
            BottomZCm = 0.0f;
            TopZCm = FMath::Min(RoomHeightCm, 150.0f);
        }

        const FVector ABottom = FVector(A2D.X, A2D.Y, BottomZCm);
        const FVector BBottom = FVector(B2D.X, B2D.Y, BottomZCm);
        const FVector ATop = FVector(A2D.X, A2D.Y, TopZCm);
        const FVector BTop = FVector(B2D.X, B2D.Y, TopZCm);

        const FColor Color = IsDoor ? FColor::Green : (IsWindow ? FColor::Yellow : FColor::White);

        DrawDebugLine(GetWorld(), ABottom, BBottom, Color, true, 0.0f, 8, 10.0f);
        DrawDebugLine(GetWorld(), ATop, BTop, Color, true, 0.0f, 8, 10.0f);
        DrawDebugLine(GetWorld(), ABottom, ATop, Color, true, 0.0f, 8, 10.0f);
        DrawDebugLine(GetWorld(), BBottom, BTop, Color, true, 0.0f, 8, 10.0f);
    }
}

void ALayoutLensVisualizerActor::SpawnFloorElements(const FLayoutLensRoomPlan& Plan)
{
    for (const FLayoutLensElement& Element : Plan.Elements)
    {
        if (!Element.Placement.Equals(TEXT("floor"), ESearchCase::IgnoreCase))
        {
            continue;
        }

        const float WidthCm = Element.WidthMeters * 100.0f;
        const float DepthCm = Element.DepthMeters * 100.0f;
        const float HeightCm = Element.HeightMeters * 100.0f;

        const float Z = HeightCm * 0.5f;
        const FVector Location = FVector(Element.Transform.X * 100.0f, Element.Transform.Y * 100.0f, Z);
        const FRotator Rotation = FRotator(0.0f, Element.Transform.YawDeg, 0.0f);

        FActorSpawnParameters SpawnParams;
        SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

        ALayoutLensPlaceholderActor* Placeholder = GetWorld()->SpawnActor<ALayoutLensPlaceholderActor>(Location, Rotation, SpawnParams);
        if (Placeholder == nullptr)
        {
            continue;
        }

        Placeholder->SetBoxSizeCm(FVector(WidthCm, DepthCm, HeightCm));

        if (SpawnLabels)
        {
            const FString LabelText = FString::Printf(TEXT("%s\n(%s)"), *Element.Label, *Element.Id);
            Placeholder->SetLabelText(LabelText);
        }
        else
        {
            Placeholder->SetLabelText(TEXT(""));
        }

        SpawnedActors.Add(Placeholder);
    }
}

void ALayoutLensVisualizerActor::SpawnWallMeshes(const FLayoutLensRoomPlan& Plan)
{
    const int32 PointCount = Plan.Boundary.Num();
    if (PointCount < 2)
    {
        return;
    }

    const float WallHeightCm = Plan.RoomHeightMeters * 100.0f;
    const float WallZ = WallHeightCm * 0.5f;

    for (int32 Index = 0; Index < PointCount; Index++)
    {
        const int32 NextIndex = (Index + 1) % PointCount;

        const FVector PointA = FVector(Plan.Boundary[Index].X * 100.0f, Plan.Boundary[Index].Y * 100.0f, WallZ);
        const FVector PointB = FVector(Plan.Boundary[NextIndex].X * 100.0f, Plan.Boundary[NextIndex].Y * 100.0f, WallZ);

        const FVector Delta = PointB - PointA;
        const float LengthCm = Delta.Size();
        if (LengthCm < 1.0f)
        {
            continue;
        }

        const FVector Center = (PointA + PointB) * 0.5f;
        const float YawDeg = FMath::RadiansToDegrees(FMath::Atan2(Delta.Y, Delta.X));
        const FRotator Rotation = FRotator(0.0f, YawDeg, 0.0f);

        FActorSpawnParameters SpawnParams;
        SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

        ALayoutLensPlaceholderActor* WallActor = GetWorld()->SpawnActor<ALayoutLensPlaceholderActor>(Center, Rotation, SpawnParams);
        if (WallActor == nullptr)
        {
            continue;
        }

        WallActor->SetBoxSizeCm(FVector(LengthCm, WallThicknessCm, WallHeightCm));
        WallActor->SetLabelText(TEXT(""));

        SpawnedActors.Add(WallActor);
    }
}

void ALayoutLensVisualizerActor::BindReloadHotkey()
{
    APlayerController* PlayerController = GetWorld() != nullptr ? GetWorld()->GetFirstPlayerController() : nullptr;
    if (PlayerController == nullptr)
    {
        return;
    }

    EnableInput(PlayerController);

    if (InputComponent != nullptr)
    {
        InputComponent->BindKey(EKeys::R, IE_Pressed, this, &ALayoutLensVisualizerActor::ReloadLayoutHotkey);
    }
}

void ALayoutLensVisualizerActor::ReloadLayoutHotkey()
{
    ReloadLayout();
}