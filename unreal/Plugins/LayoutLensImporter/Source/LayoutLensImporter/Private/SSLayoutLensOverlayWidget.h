#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

class ALayoutLensVisualizerActor;

class SLayoutLensOverlayWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SLayoutLensOverlayWidget) {}
        SLATE_ARGUMENT(TWeakObjectPtr<ALayoutLensVisualizerActor>, VisualizerActor)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

private:
    FReply OnReloadClicked();
    void OnPathTextChanged(const FText& NewText);

    TWeakObjectPtr<ALayoutLensVisualizerActor> VisualizerActor;
    FText CurrentPathText;
    TSharedPtr<class STextBlock> StatusText;
};