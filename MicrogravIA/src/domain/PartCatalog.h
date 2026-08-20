#pragma once

#include <array>

#include "core/OperationResult.h"
#include "domain/MarkingProgram.h"

class PartCatalog {
public:
    PartCatalog();
    OperationResult<const MarkingProgram*> find(PartId partId) const;

private:
    std::array<MarkingProgram, 2> programs_{};
};
