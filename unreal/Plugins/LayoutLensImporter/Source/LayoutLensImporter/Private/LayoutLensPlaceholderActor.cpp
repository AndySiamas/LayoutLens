#include "LayoutLensPlaceholderActor.h"

#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "UObject/ConstructorHelpers.h"

ALayoutLensPlaceholderActor::ALayoutLensPlaceholderActor()
{
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    BoxMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BoxMesh"));
    BoxMesh->SetupAttachment(Root);
    BoxMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

    Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Label"));
    Label->SetupAttachment(Root);
    Label->SetHorizontalAlignment(EHorizTextAligment::EHTA_Center);
    Label->SetVerticalAlignment(EVerticalTextAligment::EVRTA_TextCenter);
    Label->SetWorldSize(24.0f);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMeshFinder(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (CubeMeshFinder.Succeeded())
    {
        BoxMesh->SetStaticMesh(CubeMeshFinder.Object);
    }
}

void ALayoutLensPlaceholderActor::SetBoxSizeCm(const FVector& BoxSizeCm)
{
    FVector SafeSizeCm = BoxSizeCm;
    SafeSizeCm.X = FMath::Max(SafeSizeCm.X, 1.0f);
    SafeSizeCm.Y = FMath::Max(SafeSizeCm.Y, 1.0f);
    SafeSizeCm.Z = FMath::Max(SafeSizeCm.Z, 1.0f);

    const FVector DefaultCubeSizeCm = FVector(100.0f, 100.0f, 100.0f);
    const FVector Scale = FVector(
        SafeSizeCm.X / DefaultCubeSizeCm.X,
        SafeSizeCm.Y / DefaultCubeSizeCm.Y,
        SafeSizeCm.Z / DefaultCubeSizeCm.Z
    );

    BoxMesh->SetRelativeScale3D(Scale);

    const float LabelZ = SafeSizeCm.Z * 0.5f + 30.0f;
    Label->SetRelativeLocation(FVector(0.0f, 0.0f, LabelZ));
}

void ALayoutLensPlaceholderActor::SetLabelText(const FString& Text)
{
    Label->SetText(FText::FromString(Text));
}