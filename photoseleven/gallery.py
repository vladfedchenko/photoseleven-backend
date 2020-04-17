import datetime
from flask import Blueprint, current_app, request, Response, stream_with_context, g, jsonify, make_response, url_for
from photoseleven.auth import login_required
from photoseleven.db import get_db
from photoseleven.error import only_multimedia_content, response_fail, only_json_content
from PIL import Image, ExifTags
import os

bp = Blueprint('gallery', __name__, url_prefix='/api/gallery')


class GalleryErrors:
    GAL_ERR_MEDIA_EXISTS = 'GAL_ERR_MEDIA_EXISTS'
    GAL_ERR_MEDIA_NOT_EXIST = 'GAL_ERR_MEDIA_NOT_EXIST'
    GAL_ERR_UNSUPPORTED = 'GAL_ERR_UNSUPPORTED'
    GAL_ERR_NO_TAGS = 'GAL_ERR_NO_TAGS'

    # Get updates section
    GAL_ERR_UPD_DATA_ABSENT = 'GAL_ERR_UPD_DATA_ABSENT'


@bp.route('/media/<filename>', methods=('GET', 'POST'))
@login_required
def media(filename: str):
    """To post and get multimedia files"""

    chunk_size = 102400  # 100 KB

    @only_multimedia_content
    def post_multimedia(filename: str):
        if len(filename) < 3 or filename[-3:] not in current_app.config['ALLOWED_MEDIA_EXT']:
            return response_fail(GalleryErrors.GAL_ERR_UNSUPPORTED, 403)

        save_dir = os.path.join(current_app.config['UPLOADS_DIR'], g.user['username'])
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        if os.path.exists(save_path):
            # Emptying the stream before sending error
            while True:
                chunk = request.stream.read(chunk_size)
                if len(chunk) == 0:
                    break
            return response_fail(GalleryErrors.GAL_ERR_MEDIA_EXISTS, 403)

        with open(save_path, 'wb') as media_file:
            while True:
                chunk = request.stream.read(chunk_size)
                if len(chunk) == 0:
                    break
                media_file.write(chunk)

        img = Image.open(save_path)
        tags = {ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS}

        if 'DateTimeOriginal' not in tags or 'SubsecTimeOriginal' not in tags:
            return response_fail(GalleryErrors.GAL_ERR_MEDIA_EXISTS, 422)
            pass

        dt_part = tags['DateTimeOriginal'].split()
        assert len(dt_part) == 2
        dt = f"{dt_part[0].replace(':', '-')} {dt_part[1]}.{tags['SubsecTimeOriginal']}"

        db = get_db()
        db[f'{g.user["username"]}_updates'].insert_one({'filename': filename,
                                                        'is_new_photo': True,
                                                        'uploaded_at': datetime.datetime.now(),
                                                        'created_at': dt,
                                                        'uploader_token': g.token,
                                                        'request_path': url_for('gallery.media', filename=filename)})

        request.close()
        return make_response(jsonify({'success': True, 'request_path': url_for('gallery.media', filename=filename)}),
                             201)

    if request.method == 'POST':
        return post_multimedia(filename)

    if request.method == 'GET':
        if len(filename) < 3 or filename[-3:] not in current_app.config['ALLOWED_MEDIA_EXT']:
            return response_fail(GalleryErrors.GAL_ERR_UNSUPPORTED, 403)

        load_path = os.path.join(current_app.config['UPLOADS_DIR'], g.user['username'], filename)
        if not os.path.exists(load_path):
            return response_fail(GalleryErrors.GAL_ERR_MEDIA_NOT_EXIST, 403)

        def generate(file_path):
            with open(file_path, 'rb') as media_file:
                while True:
                    chunk = media_file.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        return Response(stream_with_context(generate(load_path)),
                        mimetype=current_app.config['ALLOWED_MEDIA_EXT'][filename[-3:]])


@bp.route('/get_updates', methods=['GET'])
@login_required
@only_json_content
def get_updates(data):
    """To get updates uploaded by other clients"""
    if 'last_updated' not in data or 'fetch_num' not in data:
        return response_fail(GalleryErrors.GAL_ERR_UPD_DATA_ABSENT, 422)

    last_updated = datetime.datetime.fromisoformat(data['last_updated'])
    n = data['fetch_num']

    db = get_db()
    query = db[f'{g.user["username"]}_updates'] \
        .find({'uploader_token': {'$ne': g.token},
               'uploaded_at': {'$gt': last_updated}}) \
        .sort('uploaded_at') \
        .limit(n)

    res = [{'created_at': d['created_at'],
            'filename': d['filename'],
            'request_path': d['request_path'],
            'uploaded_at': str(d['uploaded_at'])} for d in query]

    return make_response(jsonify({'success': True, 'data': res}), 200)
