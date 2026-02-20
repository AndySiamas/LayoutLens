#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LayoutLensPlaceholderActor.generated.h"

UCLASS()
class LAYOUTLENSIMPORTER_API ALayoutLensPlaceholderActor : public AActor
{
    GENERATED_BODY()

public:
    ALayoutLensPlaceholderActor();

    void SetBoxSizeCm(const FVector& BoxSizeCm);
    void SetLabelText(const FString& Text);

private:
    UPROPERTY()
    TObjectPtr<USceneComponent> Root;

    UPROPERTY()
    TObjectPtr<class UStaticMeshComponent> BoxMesh;

    UPROPERTY()
    TObjectPtr<class UTextRenderComponent> Label;
};