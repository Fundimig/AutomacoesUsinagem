#include "domain/PartCatalog.h"

PartCatalog::PartCatalog() {
    programs_[0].partId = PartId::Part031;
    programs_[1].partId = PartId::Part045;
    // V0.1 safety lock: no real marking parameters have been approved.
    programs_[0].configured = false;
    programs_[0].validatedForProduction = false;
    programs_[1].configured = false;
    programs_[1].validatedForProduction = false;
}

OperationResult<const MarkingProgram*> PartCatalog::find(PartId partId) const {
    for (const auto& program : programs_) {
        if (program.partId == partId) {
            return OperationResult<const MarkingProgram*>::success(&program);
        }
    }
    return OperationResult<const MarkingProgram*>::failure(
        SystemErrorCode::ProgramNotFound, "Marking program not found");
}
