"""Owner-scoped group try-on requests and background processing."""
from dataclasses import asdict
from io import BytesIO
import json
import logging
import uuid

from fastapi import HTTPException
from PIL import Image

from app.application.ports.visualisation_repository import connection, get_vton_adapter, runtime, utcnow
from app.application.visualisation.personal_image_service import require_person
from app.application.visualisation.outfit_identifier_validator import resolve_source
from app.domain.value_objects.visualisation_plan import VisualisationPlan, VisualisationGarment, VTONConfiguration
from app.domain.value_objects.generated_visualisation import VTONFailure
from app.infrastructure.ai.group_person_detection import detect_people, DetectedPerson
from app.infrastructure.ai.group_vton_pipeline import render_group
from app.infrastructure.ai.vton_preprocessing import compose_layered_upper_garments, encode_png

LOGGER = logging.getLogger(__name__)


def detect(user_id, profile_id, person_image_id):
    with connection() as conn:
        person = require_person(conn, person_image_id, user_id, profile_id)
        media_id = person['media_id']
    payload = runtime().media.path_for_owner(media_id, user_id)[0].read_bytes()
    from app.infrastructure.ai.vton_preprocessing import decode_rgb
    width, height = decode_rgb(payload).size
    with runtime().gpu_slot():
        people = detect_people(payload)
    if not people:
        raise HTTPException(422, 'No people were detected. Choose a clearer group photo.')
    detections = []
    for person in people:
        mask_id = runtime().media.store_bytes(encode_png(person.mask), user_id, 'group_person_mask', 'image/png')
        detections.append({'box': person.box, 'confidence': person.confidence, 'mask_media_id': mask_id})
    identifier, now = str(uuid.uuid4()), utcnow()
    with connection() as conn:
        require_person(conn, person_image_id, user_id, profile_id)
        conn.execute('INSERT INTO group_visualisations (id,user_id,profile_id,person_image_id,person_media_id,detections_json,status,created_at,updated_at) VALUES (?,?,?,?,?,?,\'draft\',?,?)',
                     (identifier, user_id, profile_id, person_image_id, media_id, json.dumps(detections), now, now))
    return {'id': identifier, 'width': width, 'height': height, 'people': [{'index': i, 'box': d['box'], 'confidence': d['confidence']} for i, d in enumerate(detections)]}


def submit(user_id, profile_id, identifier, assignments):
    if not 1 <= len(assignments) <= 2 or len({a.person_index for a in assignments}) != len(assignments):
        raise HTTPException(422, 'Choose one or two different people.')
    with connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM group_visualisations WHERE id=? AND user_id=? AND profile_id=?', (identifier, user_id, profile_id)).fetchone()
        if not row or row['status'] != 'draft':
            raise HTTPException(404, 'Group draft is unavailable.')
        queued = conn.execute("SELECT (SELECT COUNT(*) FROM visualisations WHERE status='queued') + (SELECT COUNT(*) FROM group_visualisations WHERE status='queued')").fetchone()[0]
        if queued >= runtime().queue_limit:
            raise HTTPException(429, 'The try-on queue is full. Please try again shortly.')
        require_person(conn, row['person_image_id'], user_id, profile_id)
        count = len(json.loads(row['detections_json']))
        snapshots = []
        for assignment in assignments:
            if assignment.person_index < 0 or assignment.person_index >= count:
                raise HTTPException(422, 'Invalid person selection.')
            plan, _ = resolve_source(conn, user_id, assignment.outfit_id, assignment.recommendation_id)
            snapshots.append({'person_index': assignment.person_index, 'plan': asdict(plan)})
        conn.execute("UPDATE group_visualisations SET assignments_json=?,status='queued',progress_message=?,updated_at=? WHERE id=? AND status='draft'", (json.dumps(snapshots), 'Waiting for the GPU.', utcnow(), identifier))


def run(user_id, identifier):
    try:
        with runtime().gpu_slot():
            with connection() as conn:
                changed = conn.execute("UPDATE group_visualisations SET status='processing',updated_at=? WHERE id=? AND user_id=? AND status='queued'", (utcnow(), identifier, user_id)).rowcount
                if not changed:
                    return
                row = conn.execute('SELECT * FROM group_visualisations WHERE id=? AND user_id=?', (identifier, user_id)).fetchone()
            payload = runtime().media.path_for_owner(row['person_media_id'], user_id)[0].read_bytes()
            people = []
            for detection in json.loads(row['detections_json']):
                path = runtime().media.path_for_owner(detection['mask_media_id'], user_id)[0]
                with Image.open(path) as image:
                    mask = image.convert('L')
                people.append(DetectedPerson(tuple(detection['box']), detection['confidence'], mask))
            assignments = []
            for snapshot in json.loads(row['assignments_json']):
                data = snapshot['plan']
                data['garments'] = tuple(VisualisationGarment(**item) for item in data['garments'])
                data['configuration'] = VTONConfiguration(**data['configuration'])
                plan = VisualisationPlan(**data)
                with connection() as conn:
                    for garment in plan.garments:
                        existing = conn.execute("SELECT preferred_media_id,category FROM garments WHERE id=? AND user_id=? AND status='available'", (garment.garment_id, user_id)).fetchone()
                        if not existing or existing['preferred_media_id'] != garment.source_media_id or existing['category'] != garment.category:
                            raise ValueError('Outfit changed after submission.')
                images = {item.garment_id: runtime().media.path_for_owner(item.source_media_id, user_id)[0].read_bytes() for item in plan.render_garments}
                garments = tuple(compose_layered_upper_garments(tuple(images[item.garment_id] for item in step.garments)) if step.composition == 'layered_upper' else images[step.garments[0].garment_id] for step in plan.render_steps)
                assignments.append((snapshot['person_index'], plan, garments))
            def progress(index, total_people, current, total, phase):
                with connection() as conn:
                    changed = conn.execute("UPDATE group_visualisations SET progress_message=?,updated_at=? WHERE id=? AND user_id=? AND status='processing'", (f'Person {index + 1} of {total_people}: garment {min(current + 1, total)} of {total}.', utcnow(), identifier, user_id)).rowcount
                    if not changed:
                        raise ValueError('Group request is no longer active.')
            image = render_group(payload, people, assignments, get_vton_adapter(), progress)
            with connection() as conn:
                active = conn.execute("SELECT 1 FROM group_visualisations WHERE id=? AND user_id=? AND status='processing'", (identifier, user_id)).fetchone()
            if not active:
                return
            output_id = runtime().media.store_bytes(image, user_id, 'vton_output', 'image/png')
            with connection() as conn:
                conn.execute("UPDATE group_visualisations SET status='completed',output_media_id=?,progress_message=?,updated_at=? WHERE id=? AND user_id=? AND status='processing'", (output_id, 'Group preview complete.', utcnow(), identifier, user_id))
    except Exception as exc:
        LOGGER.exception('Group visualisation %s failed', identifier)
        message = str(exc) if isinstance(exc, VTONFailure) else 'Could not generate the group preview. Use a clear photo with separated people and try again.'
        if isinstance(exc, ValueError) and str(exc) in ('People overlap. Choose a photo with more separation.', 'People need space around them in the photo.', 'The model did not produce a usable preview.', 'A real CatVTON model is required for group try-on.'):
            message = str(exc)
        with connection() as conn:
            conn.execute("UPDATE group_visualisations SET status='failed',error_message=?,updated_at=? WHERE id=? AND user_id=? AND status IN ('queued','processing')", (message, utcnow(), identifier, user_id))


def get(user_id, identifier):
    with connection() as conn:
        row = conn.execute('SELECT id,status,progress_message,error_message,output_media_id FROM group_visualisations WHERE id=? AND user_id=?', (identifier, user_id)).fetchone()
    if not row:
        raise HTTPException(404, 'Group visualisation was not found.')
    return dict(row)


def cancel(user_id, identifier):
    with connection() as conn:
        changed = conn.execute("UPDATE group_visualisations SET status='cancelled',updated_at=? WHERE id=? AND user_id=? AND status IN ('draft','queued','processing')", (utcnow(), identifier, user_id)).rowcount
    if not changed:
        raise HTTPException(409, 'This group visualisation cannot be cancelled.')


def recover_interrupted_groups():
    with connection() as conn:
        conn.execute("UPDATE group_visualisations SET status='failed',error_message=?,updated_at=? WHERE status IN ('queued','processing')", ('Group try-on was interrupted by a service restart. Please submit again.', utcnow()))
