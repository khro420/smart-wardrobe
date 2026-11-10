"""Resolve new intent using the existing owned profile model; no profile writes."""
from fastapi import HTTPException
from app.application.wardrobe.profile_service import require_active_profile
from app.domain.value_objects.intended_wearer import IntendedWearer
from app.domain.value_objects.recommendation_refinement import canonical_uuid
from app.infrastructure.persistence.postgresql_repository import connection,utcnow


def resolve_wearer(user_id,profile_id=None,header_profile_id=None):
    for value in (profile_id,header_profile_id):
        if value is not None:
            try:canonical_uuid(value)
            except ValueError:raise HTTPException(422,'A canonical wearer UUID is required.') from None
    if profile_id is not None and header_profile_id is not None and profile_id!=header_profile_id:
        raise HTTPException(409,{'code':'WearerMismatch','message':'The request wearer and selected wearer disagree.'})
    with connection() as conn:
        if profile_id is None:
            rows=conn.execute("SELECT id FROM wardrobe_profiles WHERE user_id=? AND status='active' ORDER BY id",(user_id,)).fetchall()
            if not rows:
                # Reuse the established account bootstrap for legacy accounts;
                # historical readers never take this new-action branch.
                from app.application.wardrobe.profile_service import ensure_default_profile
                rows=[ensure_default_profile(conn,user_id)]
            if len(rows)!=1:
                raise HTTPException(422,{'code':'WearerSelectionRequired','message':'Choose the intended wearer before requesting an outfit.'})
            profile_id=rows[0]['id']
            if header_profile_id is not None and header_profile_id!=profile_id:
                require_active_profile(conn,user_id,header_profile_id)
                raise HTTPException(409,{'code':'WearerMismatch','message':'The selected wearer changed.'})
            origin='single_active_auto'
        else:origin='explicit'
        row=require_active_profile(conn,user_id,profile_id)
        return IntendedWearer(user_id,profile_id,row['name'],origin,utcnow())


def wearer_scope(user_id,profile_id,base_scope):
    from app.domain.value_objects.recommendation_refinement import digest
    return digest({'version':'wearer-refinement-scope-1.0.0','user_id':user_id,'wearer_profile_id':profile_id,'base_compatibility_scope_sha256':base_scope})
