from sqlalchemy.orm import Session
from backend.app.models.case import Case
from backend.app.services.rules.engine import rule_engine
from backend.app.services.ai.service import ai_diagnosis_service
from backend.app.services.comparison.models import DiagnosisComparisonResult, ComparisonStatus
from backend.app.services.comparison.comparator import comparator

class ComparisonService:
    """
    Coordinates Python Rule Engine evaluation and AI Diagnosis execution,
    then evaluates their findings side-by-side without bias or artificial overriding.
    """

    def compare_case(self, case_id: int, db: Session) -> DiagnosisComparisonResult:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return DiagnosisComparisonResult(
                case_id=case_id,
                status=ComparisonStatus.INSUFFICIENT_EVIDENCE,
                verdict_title="Case Not Found",
                explanation=f"Troubleshooting case #{case_id} was not found in the database.",
                recommended_action="Select an active troubleshooting case from the repository.",
                confidence_score=0,
                human_review_required=True,
                python_summary="Case not found.",
                ai_summary="Case not found."
            )

        # 1. Execute deterministic Python Rule Engine
        py_result = rule_engine.diagnose_case(case_id=case_id, db=db)

        # 2. Execute AI Diagnosis Layer
        ai_result = ai_diagnosis_service.diagnose_case(case_id=case_id, db=db)

        # 3. Perform independent comparison
        comparison_res = comparator.compare(
            case_id=case_id,
            py_result=py_result,
            ai_result=ai_result
        )

        return comparison_res

comparison_service = ComparisonService()
